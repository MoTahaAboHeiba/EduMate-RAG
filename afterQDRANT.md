# After Qdrant Migration

## 1. Original Problem

EduMate used ChromaDB as a local vector store.

That was fine for local development, but it was weak for Railway production because Railway containers use an ephemeral filesystem. Any vectors stored inside the container can disappear after a restart or redeploy.

The production risk was simple:

- PDFs get indexed into local ChromaDB.
- Railway restarts the container.
- Local vector files are gone.
- The RAG app starts with `0` indexed documents.
- Retrieval returns nothing, so the app becomes useless until PDFs are indexed again.

That architecture was not production-ready.

## 2. Decision

We decided to keep ChromaDB for local development and add Qdrant Cloud for production.

The switch is controlled with one environment variable:

```env
VECTOR_STORE_BACKEND=chroma
```

or:

```env
VECTOR_STORE_BACKEND=qdrant
```

Why this approach:

- ChromaDB is still useful for local testing.
- Qdrant Cloud gives persistent vector storage outside Railway.
- The rest of the app should not care which backend is active.
- `rag_chain.py` should keep calling the same vector store interface.

## 3. Vector Store Refactor

We rewrote `src/vector_store.py` into a backend-neutral facade.

It now has:

- `ChromaVectorStore`
- `QdrantVectorStore`
- `VectorStore`, which chooses the backend from `VECTOR_STORE_BACKEND`

The public methods are still available:

```python
index_pdfs()
similarity_search(query, k)
get_collection_info()
search(query, num_results)
```

Why `search()` stayed:

`rag_chain.py` already uses `vector_store.search(...)`. Removing it would have broken the app. Keeping it was the correct compatibility move.

## 4. Config Updates

We updated `src/config.py` with:

```python
VECTOR_STORE_BACKEND
QDRANT_URL
QDRANT_API_KEY
```

Qdrant is now the default backend:

```python
VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE_BACKEND", "qdrant").lower()
```

Why:

The production target is Railway, and Railway should use persistent Qdrant by default.

We also added validation:

- Invalid backend values fail fast.
- Missing Qdrant URL/key fail fast.
- Placeholder Qdrant values fail fast.

That prevents wasting time debugging a fake URL like `your_real_qdrant_url`.

## 5. Requirements Updates

We added:

```txt
qdrant-client==1.9.1
PyMuPDF==1.24.9
onnxruntime==1.18.1
```

Why:

- `qdrant-client` is required to talk to Qdrant Cloud.
- `PyMuPDF` was added because `pypdf` failed on the first PDF files.
- `onnxruntime` is required by Chroma's default embedding function.

## 6. Startup Indexing

We added a FastAPI startup hook in `src/api/main.py`.

Behavior:

- On startup, check vector count.
- If count is `0`, index PDFs.
- If count is greater than `0`, skip indexing.

Why:

Railway should be able to boot into a usable state automatically, but it should not re-index every restart when Qdrant already has vectors.

## 7. Docker Production Fix

The Dockerfile was using:

```dockerfile
--workers 2
```

We changed it to:

```dockerfile
--workers 1
```

Why:

This app has process-local conversation memory and startup indexing. Multiple workers can cause inconsistent memory and duplicate startup indexing. For this app, `1` worker is the safer production default.

## 8. First Test Problem: PowerShell Policy

Before the migration work, PowerShell printed this error:

```text
profile.ps1 cannot be loaded because running scripts is disabled
```

We fixed the user-level PowerShell execution policy:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Outcome:

PowerShell commands stopped printing the profile loading error.

## 9. First Real Blocker: Bad PDFs

Initial indexing produced:

```text
Total chunks created: 0
```

`pypdf` failed with errors such as:

```text
Cannot find Root object in pdf
Invalid Elementary Object
```

We added a PyMuPDF fallback, but the original files still extracted `0` chunks.

Conclusion:

The first PDF set was not usable for text extraction. The vector database was not the blocker; the source documents were.

After replacing the PDFs, extraction worked.

Measured result:

```text
Found 5 PDF(s)
Total chunks created: 5720
```

Later Qdrant startup extracted:

```text
Total chunks created: 5637
```

The slight difference came from using the updated loader/runtime path during the final indexing run.

## 10. Second Blocker: Broken Old Virtualenv

Running the app from the old `venv` failed with:

```text
ImportError: DLL load failed while importing _pydantic_core:
%1 is not a valid Win32 application.
```

Meaning:

The old virtualenv had broken or mismatched binary wheels. This was not a FastAPI bug.

We created a clean environment:

```powershell
.venv311
```

Using:

```text
Python 3.11.9 64-bit
```

Then installed all requirements successfully.

Outcome:

The app imported correctly from `.venv311`.

## 11. Third Blocker: Local Chroma Environment

The active Anaconda Python had:

```text
chromadb 1.3.5
```

But the project requires:

```text
chromadb 0.4.22
```

Trying to install the pinned Chroma into Anaconda failed because `chroma-hnswlib` needed Microsoft C++ Build Tools.

Conclusion:

Local Chroma testing was blocked by the local Windows/Anaconda environment, not by the application logic.

Since the production target is Qdrant, we focused on Qdrant mode.

## 12. Qdrant Startup Test

After putting real Qdrant values in `.env`, we tested Qdrant mode.

The first Qdrant run failed in the sandbox with:

```text
[WinError 10013] An attempt was made to access a socket in a way forbidden by its access permissions
```

Why:

The execution sandbox blocked outbound network access.

After allowing network access, the app connected to Qdrant.

First successful health check:

```json
{
  "status": "healthy",
  "vector_store": {
    "collection": "course_materials",
    "documents_indexed": 3909
  }
}
```

Problem:

The PDF loader produced `5637` chunks, but Qdrant only had `3909` vectors. Some Qdrant upsert batches timed out.

## 13. Qdrant Indexing Reliability Fix

Qdrant indexing initially used larger batches and synchronous writes.

Problems seen:

```text
The read operation timed out
The write operation timed out
```

We improved the Qdrant indexer:

- Increased Qdrant client timeout to `120`.
- Reduced batch size from `64` to `32`.
- Added retry logic for failed batches.
- Changed Qdrant upserts from `wait=True` to `wait=False`.

Why:

For large indexing jobs, waiting synchronously on every batch caused timeouts. Asynchronous writes are better for getting accepted writes into Qdrant without blocking the app for too long.

Measured outcome:

- First successful Qdrant app health: `3909` vectors.
- After retry-based re-index: `5349` vectors.
- After async upsert re-index: `5573` vectors.
- After targeted missing-vector repair: `5637` vectors.

Final verified state:

```json
{
  "status": "healthy",
  "vector_store": {
    "collection": "course_materials",
    "documents_indexed": 5637
  }
}
```

## 14. Targeted Repair

Full re-indexing was too slow and hit command timeouts.

Instead of brute-forcing the whole dataset again, we compared deterministic point IDs against Qdrant and uploaded only missing vectors.

Result:

```text
MISSING 64
UPSERTED_MISSING 64 / 64
INFO_AFTER {'collection_name': 'course_materials', 'count': 5637}
```

Why:

The vector IDs are deterministic, so re-uploading missing points is safe and does not create duplicates.

## 15. Final Outcome

Current production-ready behavior:

- Qdrant is the default vector backend.
- Vectors are stored persistently in Qdrant Cloud.
- Railway restarts will not wipe indexed vectors.
- Startup checks document count before indexing.
- If vectors already exist, startup skips re-indexing.
- PDFs now extract successfully.
- Qdrant contains all indexed chunks.
- The app runs successfully from `.venv311`.

Final verified command:

```powershell
.\.venv311\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8020
```

Final verified health:

```json
{
  "status": "healthy",
  "model": "llama-3.3-70b-versatile",
  "vector_store": {
    "collection": "course_materials",
    "documents_indexed": 5637
  }
}
```

## 16. What Improved

Before:

- Local Chroma only.
- Railway could lose vectors after restart.
- Broken PDFs produced `0` chunks.
- Old virtualenv could not even import FastAPI correctly.
- Qdrant was not available.

After:

- Qdrant Cloud is supported and is the default.
- Railway can persist vectors outside the container.
- PDFs extract into thousands of chunks.
- Qdrant contains `5637` indexed chunks.
- App starts successfully in Qdrant mode.
- Startup indexing is conditional.
- Indexing uses retries and deterministic IDs.
- `.venv311` gives a clean local runtime.

## 17. How To Run Now

Use the clean environment:

```powershell
cd "D:\College 🏛\Final Project\edumate\EduMate-RAG"
.\.venv311\Scripts\Activate.ps1
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

Then check:

```text
http://127.0.0.1:8000/health
```

Expected:

```json
{
  "documents_indexed": 5637
}
```

## 18. Railway Environment Variables

Set these in Railway:

```env
VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=your_real_qdrant_cloud_url
QDRANT_API_KEY=your_real_qdrant_api_key
GROQ_API_KEY=your_real_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile
```

Do not put real secrets in `.env.example`.

`.env.example` is public documentation only.

