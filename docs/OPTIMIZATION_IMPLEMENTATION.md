Incremental Indexing and Optimization Implementation

OVERVIEW
This implementation adds four major optimizations to EduMate-RAG indexing:
1. File modification tracking for incremental processing
2. Embedding cache to avoid re-computing embeddings
3. Parallel PDF processing using ThreadPoolExecutor
4. Incremental upsert vs full re-indexing

FILES MODIFIED
- src/document_processing/file_tracker.py (NEW)
- src/document_processing/embedding_cache.py (NEW)
- src/document_processing/pdf_loader.py (MODIFIED)
- src/document_processing/vector_store.py (MODIFIED)
- src/api/main.py (MODIFIED)

IMPLEMENTATION DETAILS

1. FILE MODIFICATION TRACKING (file_tracker.py)
--------------------------------------------------
Purpose: Detect which PDF files have changed since last indexing

Class: FileTracker
- Stores file modification times and sizes in .cache/file_tracking/file_metadata.json
- Methods:
  - is_changed(file_path): Returns True if file is new or modified
  - get_changed_files(pdf_files): Partitions files into changed/unchanged lists
  - mark_processed(file_path): Records current file state after processing
  - clear_tracking(): Resets all tracking metadata

Usage in PDFLoader:
```python
changed_files, unchanged_files = file_tracker.get_changed_files(pdf_files)
# Only process changed_files
for pdf_file in changed_files:
    docs = loader._load_pdf(pdf_file)
    file_tracker.mark_processed(pdf_file)
```

Impact: Reduces indexing time by only processing changed PDFs
Cache location: .cache/file_tracking/file_metadata.json

2. EMBEDDING CACHE (embedding_cache.py)
--------------------------------------
Purpose: Store computed embeddings to avoid re-computation

Class: EmbeddingCache
- Uses SHA256 hashing of text content as cache key
- Stores embeddings in .cache/embeddings/embeddings.json
- Methods:
  - get(text): Retrieve cached embedding for exact text
  - get_batch(texts): Efficiently batch lookup with parallel fetching
  - set(text, embedding): Cache single embedding
  - set_batch(texts, embeddings): Cache multiple embeddings at once
  - get_stats(): Return cache statistics
  - clear(): Reset all cached embeddings

Smart Batch Processing:
```python
cached, missing_indices, missing_texts = embedding_cache.get_batch(texts)
# Only compute missing embeddings
new_embeddings = embedding_function(missing_texts)
embedding_cache.set_batch(missing_texts, new_embeddings)
```

Impact: Skip embedding computation for unchanged text chunks
Cache location: .cache/embeddings/embeddings.json

3. PARALLEL PDF PROCESSING (pdf_loader.py)
-----------------------------------------
Purpose: Load and process multiple PDFs concurrently

Class: PDFLoader (updated)
- Added ThreadPoolExecutor with configurable max_workers (default: 4)
- Methods:
  - load_all_pdfs(incremental=True): Main entry point
  - _load_pdfs_parallel(pdf_files): Parallel processing implementation

Incremental Mode:
```python
if incremental:
    changed_files, unchanged_files = file_tracker.get_changed_files(pdf_files)
    print(f"Processing: {len(changed_files)} changed, {len(unchanged_files)} unchanged")
    pdf_files_to_process = changed_files
```

Parallel Processing:
```python
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(_load_pdf, path): path for path in files}
    for future in as_completed(futures):
        docs = future.result()
        documents.extend(docs)
```

Impact: N PDFs processed in parallel instead of sequentially
Thread-safe with internal lock for shared document list

4. INCREMENTAL VECTOR STORE INDEXING (vector_store.py)
-----------------------------------------------------
Purpose: Support incremental indexing with caching

ChromaVectorStore & QdrantVectorStore Updates:
- index_pdfs(incremental=True, force_full=False)
  - incremental: Use file change detection (default True)
  - force_full: Ignore tracking and re-index everything (default False)

- _embed_texts_with_cache(texts): Embedding with cache integration
  - Check cache for each text
  - Compute only missing embeddings
  - Store new embeddings for future use

Batch Processing:
```python
batch_size = 64  # Chroma, 32 for Qdrant
for start in range(0, len(documents), batch_size):
    batch = documents[start:start + batch_size]
    embeddings = self._embed_texts_with_cache(batch_texts)
    vector_store.add/upsert(...)
```

Qdrant uses upsert() to handle duplicate IDs automatically
ChromaDB uses add() - existing IDs are preserved

API ENDPOINTS

1. POST /api/index
   Query Parameters:
   - incremental: bool (default: True) - Use incremental indexing
   - force_full: bool (default: False) - Force full re-indexing
   
   Response:
   {
       "status": "success",
       "message": "PDFs indexed successfully",
       "documents_indexed": 150,
       "indexing_mode": "incremental"
   }

2. GET /api/cache/stats (requires X-Admin-Key header)
   Response:
   {
       "status": "success",
       "embedding_cache": {
           "total_cached": 1250,
           "cache_file": ".cache/embeddings/embeddings.json",
           "cache_size_bytes": 45000
       },
       "file_tracking": {
           "tracked_files": 5,
           "tracker_file": ".cache/file_tracking/file_metadata.json"
       }
   }

3. POST /api/cache/clear (requires X-Admin-Key header)
   Query Parameters:
   - clear_embeddings: bool (default: True)
   - clear_tracking: bool (default: False)
   
   Response:
   {
       "status": "success",
       "message": "Cache cleared successfully",
       "cleared": ["embedding_cache"]
   }

USAGE EXAMPLES

Example 1: First Time Indexing (Full)
```bash
curl -X POST http://localhost:8000/api/index \
  -H "X-Admin-Key: graduation-demo-key" \
  -H "Content-Type: application/json" \
  -d '{"force_full": true, "incremental": false}'
```

Example 2: Incremental Indexing (Default)
```bash
curl -X POST http://localhost:8000/api/index \
  -H "X-Admin-Key: graduation-demo-key"
```
Only changed PDFs are processed, embeddings are cached

Example 3: View Cache Statistics
```bash
curl -X GET http://localhost:8000/api/cache/stats \
  -H "X-Admin-Key: graduation-demo-key"
```

Example 4: Clear Cache and Force Re-index
```bash
curl -X POST http://localhost:8000/api/cache/clear \
  -H "X-Admin-Key: graduation-demo-key" \
  -d "clear_embeddings=true&clear_tracking=true"

curl -X POST http://localhost:8000/api/index \
  -H "X-Admin-Key: graduation-demo-key" \
  -d "force_full=true"
```

PERFORMANCE CHARACTERISTICS

Indexing Time Comparison (hypothetical):
- Full sequential: 60s (5 PDFs, 50 chunks each)
- Parallel (4 workers): 15s (4x speedup)
- Incremental (1 changed PDF): 3s (20x speedup)
- With embedding cache: 1s (60x speedup)

Typical workflow:
1. First run: Full sequential indexing
2. Subsequent runs: Incremental + cached embeddings
3. On PDF changes: Only changed PDFs processed
4. Cache benefits grow with corpus size

CONFIGURATION

File Tracking:
- Location: .cache/file_tracking/file_metadata.json
- Format: {file_path: [mtime, size], ...}
- Clear with: POST /api/cache/clear?clear_tracking=true

Embedding Cache:
- Location: .cache/embeddings/embeddings.json
- Format: {sha256_hash: [embedding_vector], ...}
- Clear with: POST /api/cache/clear?clear_embeddings=true

Parallel Processing:
- Default workers: 4 (configurable in __init__)
- Thread-safe: Yes (internal locking)
- Memory: Bounded by batch_size parameter

DEBUGGING

Enable detailed logging:
```python
# Monitor file tracking
print(file_tracker.file_metadata)

# Check cache statistics
print(embedding_cache.get_stats())

# Verify cache hits
# Look for "cached" vs "computed" in embedding logs
```

Common Issues:
1. Cache not reducing time:
   - Check: POST /api/cache/stats
   - Solution: Restart to clear in-memory state

2. Old embeddings being used:
   - Solution: POST /api/cache/clear?clear_embeddings=true

3. Stale file tracking:
   - Solution: POST /api/cache/clear?clear_tracking=true

MIGRATION GUIDE

From Old System:
- No breaking changes - backward compatible
- Old index_pdfs() calls work unchanged
- New parameters are optional with sensible defaults
- Gradually enable optimization features

Recommended Rollout:
1. Deploy with incremental=True (automatic)
2. Monitor file_tracking effectiveness
3. Enable embedding_cache once cache size stabilizes
4. Use force_full=True for manual re-indexing if needed

FUTURE ENHANCEMENTS

Potential improvements:
1. Distributed caching (Redis/Memcached)
2. Vectorized embedding computation
3. Async/await for I/O operations
4. Document diffing for partial updates
5. LRU eviction policy for embedding cache
6. Persistent thread pool for API server
