# EduMate-RAG — AI Agent Handoff Document
> **Read this file first. It replaces ~10,000 tokens of conversation history.**  
> **Last updated: 2026-06-12**

---

## 1. Project Identity (30 seconds)

**What it is:** RAG system for university CS students. Answers questions from indexed course PDFs.  
**Stack:** FastAPI → Qdrant Cloud (vector store) → Groq LLM (`llama-3.3-70b-versatile`)  
**Purpose:** Graduation project + portfolio. NOT production. Scalability/CI/CD are non-goals.  
**Python:** 3.11 (venv at `.venv311/`)  
**Run locally:** `python run_dev.py` → FastAPI on `localhost:8000`

---

## 2. Critical Environment Facts

```
# .env (DO NOT COMMIT — already gitignored)
VECTOR_STORE_BACKEND=qdrant          ← Cloud Qdrant, NOT local ChromaDB
QDRANT_URL=https://a947d7d1-...      ← Cloud instance
GROQ_API_KEY=gsk_3ug...              ← Primary key (hits rate limits fast)
GROQ_API_KEY_2=gsk_VQM...           ← Fallback key
GROQ_MODEL=llama-3.3-70b-versatile
ADMIN_KEY=graduation-demo-key
```

**Rate limit reality:** Groq free tier = ~30 RPM. Full 85-query evaluation consistently hits the limit at query ~18-20. This is why full evaluation runs have never completed cleanly.

---

## 3. Repository Map — Read Only What You Need

**Best presentation files:**
- `README.md` — main product story, architecture, and API usage
- `OPTIMIZATION_SUMMARY.md` — concise optimization highlights for slide-ready talking points
- `OPTIMIZATION_IMPLEMENTATION.md` — technical detail if asked for deeper implementation or reviewer questions
- `AGENT_HANDOFF.md` — handoff-level project status, known bugs, and evaluation history

```
src/
  config/config.py           ← Config singleton. Validates GROQ_API_KEY at import time.
  core/rag_chain.py          ← Main orchestrator (418 lines). query() method = lines 121-301.
  core/retrieval_optimizer.py ← RetrievalOptimizer (234 lines). optimize_retrieval() = lines 173-230.
  document_processing/
    file_tracker.py          ← File change tracking for incremental indexing.
    embedding_cache.py       ← SHA256-based embedding cache for text embeddings.
    vector_store.py          ← VectorStore facade for Qdrant/ChromaDB with incremental mode.
    pdf_loader.py            ← PDF ingestion, chunking, and parallel load.
  api/main.py                ← FastAPI app (349 lines). All routes are SYNC (not async).

evaluation/
  datasets/
    rag_evaluation_dataset_v1.json   ← 85 QA pairs. Ground truth = PDF filename strings.
  metrics/
    metrics_calculator.py    ← Metric formulas (336 lines). RetrievalMetrics dataclass here.
  run_evaluation.py          ← Full eval harness (calls API + Groq). DO NOT use to avoid rate limits.
  analyze_results.py         ← Reads result files, generates HTML reports.
  evaluation_config.json     ← Metric targets: P@3≥0.70, Recall@5≥0.60, MRR≥0.75, NDCG@10≥0.70
  results/                   ← All past result JSON files (see Section 5).

docs/
  OPTIMIZATION_IMPLEMENTATION.md ← Detailed optimization implementation guide.
  OPTIMIZATION_SUMMARY.md        ← Quick optimization reference.
- `phase1_brutal_review.md`, `phase2_architecture_attack.md` — older AI review sessions
- `server.out.log`, `server.err.log` — runtime logs
- `docs/` — user-facing documentation

---

## 4. Known Bugs (Evidence-Based, Not Assumptions)

### BUG-1 — Similarity filtering permanently disabled in production
**File:** `src/core/rag_chain.py:172`  
```python
retrieved_docs = retrieval_optimizer.optimize_retrieval(
    ...
    similarity_threshold=0.0   # ← BUG: 0.0 disables filtering
)
```
**Guard in optimizer** (`retrieval_optimizer.py:204`): `if similarity_threshold > 0:` — 0.0 never enters.  
**Impact:** No irrelevant docs are filtered. Dedup and rerank still run.  
**Fix:** Change `similarity_threshold=0.0` to a tuned value (0.3 is a reasonable start).

### BUG-2 — `max_memory_messages` is dead code
**File:** `src/core/rag_chain.py:102`  
`self.max_memory = max_memory_messages` is stored but **never read anywhere else**.  
Memory grows unboundedly per session. Not critical for single-user demo.

### BUG-3 — `_is_general_question` has untested boundary case
**File:** `src/core/rag_chain.py:303-317`  
Pattern `'hi '` (with trailing space) — `"Hi, what is pipelining?"` would be misclassified as a greeting and skip all retrieval. Untested.

### BUG-4 — `evaluate_generation` in metrics_calculator.py is a stub
**File:** `evaluation/metrics/metrics_calculator.py:253-257`  
```python
faithfulness = 0.8   # ← hardcoded constants, ignores all inputs
relevance = 0.85
completeness = 0.75
```
The actual varying faithfulness values in result files come from `run_evaluation.py`'s own compute path, not this method.

### BUG-5 — Key rotation tests test a copy, not the actual RAGChain
**File:** `tests/unit/test_key_rotation.py:54-77`  
Comment in file: "Inline re-implementation of the generation try/except block". If `rag_chain.py` changes its error handling, these tests will still pass.

### BUG-6 — Ground truth is document-level (PDF filename), not chunk-level
**Dataset:** `evaluation/datasets/rag_evaluation_dataset_v1.json`  
Every `ground_truth_docs` = `["<PDF filename string>"]`. Retrieving ANY chunk from the correct PDF counts as a hit. Precision/Recall metrics are easier to satisfy than they appear.

---

## 5. Evaluation History — What Results Can Be Trusted

| Result File | Date | Queries | Trust? | Notes |
|---|---|---|---|---|
| `phase3_results_20260518_164107.json` | May 18 | 85 | ❌ NO | Old code: Recall > 1.0 (bug), faithfulness = hardcoded 0.8 |
| `phase3_results_20260519_*.json` | May 19 | 66-85 | ❌ NO | Same old code bugs |
| `phase3_results_20260601_*.json` | Jun 1 | 5-13 | ❌ NO | Rate-limited, too small |
| `phase3_results_20260609_144322.json` | Jun 9 | 66 | ⚠️ PARTIAL | Pre-fix code, 19 failures |
| `phase3_results_20260611_181522.json` | Jun 11 | **18** | ⚠️ PARTIAL | Post-fix code, rate-limited at query 19 |
| `retrieval_eval_20260612_151417.json` | Jun 12 | **85** | ⚠️ PARTIAL | Standalone baseline. Had 25/85 failures due to missing OS PDF and naming mismatch. |
| `retrieval_eval_20260612_160420.json` | Jun 12 | **73** | ✅ YES | Clean baseline evaluation run on sanitized dataset (pruned missing OS, fixed naming mismatch). |
| `generation_eval_20260615_160040.json` | Jun 15 | **10** | ✅ YES | Generation evaluation baseline (easy stratum). Source accuracy 1.0, MCF 0.572, NLI relevance 0.763, Groq relevance 0.940, Groq completeness 0.840. |

**Critical:** A fully trusted baseline has been established on the cleaned 73-query dataset.

**Old Recall > 1.0 bug (now fixed in code):**  
Old code computed `sum(1 for doc in top_k if doc in ground_truth)` (counting duplicates) divided by `len(ground_truth)`. With 5 retrieved chunks all from same PDF and 1 ground truth doc: `5/1 = 5.0`. Current code uses `set(top_k)` to deduplicate first → Recall is now bounded [0,1].

---

## 6. Phase Status

### ✅ COMPLETED
- PDF Ingestion and Indexing (5 PDFs in Qdrant, 4 PDFs in local ChromaDB)
- FastAPI backend (functional)
- Basic RAG pipeline (functional, BUG-1 notwithstanding)
- Groq key rotation on rate limit
- Unit tests scaffold (3 files, 13 tests total)
- `metrics_calculator.py` Recall dedup fix (code fixed, not yet re-run)
- Full technical review and bug documentation (this document)
- **TASK A** — Fixed `metrics_calculator.py` by adding expanded metrics (Precision@1, @10, Recall@1, @3, @10, NDCG@5, HitRate@1, @3, @5, @10), bounds assertions, and empty ground truth handling.
- **TASK B** — Created `evaluation/retrieval_eval.py` supporting unbuffered output, relative path formatting, local ChromaDB backend overrides, and 2x4 parameter grid experiments.
- **TASK C** — Successfully executed offline retrieval evaluation baseline (680 database queries) and stored JSON report.
- **TASK D** — Updated `README.md` and `AGENT_HANDOFF.md` with validated baseline results and detailed failure analysis findings.
- **Resolved Data Quality & Evaluation Discrepancies (Option A)** — Standardized textbook reference naming and pruned missing Operating Systems queries to establish a clean 73-query evaluation dataset. Re-run baseline evaluations to establish verified metrics.
- **Generation Evaluation Baseline** — Successfully executed initial generation evaluation run (10-query easy stratum subset) measuring MCF, source accuracy, NLI relevance, and Groq judge metrics (using llama-3.3-70b-versatile). Identified conversational preamble dilution impact on MCF.

### 🔄 DECIDED BUT NOT IMPLEMENTED
None. All phase baseline tasks are complete.

### ❌ NOT STARTED (Future Phases)
- Chunk-level ground truth (high effort, defer until document-level baseline is trusted)
- Cross-encoder reranking
- Better embedding model (bge-base, mpnet)
- Fix `similarity_threshold=0.0` call site (BUG-1) — done after baseline confirms impact
- Real faithfulness evaluation (NLI-based, not LLM-based) — Initial framework implemented in metrics and generation_eval.py.
- Memory truncation (fix dead `max_memory_messages` parameter)

---

## 7. Architecture Quick Reference

### How a query flows
```
User query
→ api/main.py: POST /api/query (sync route)
→ rag_chain.py: RAGChain.query()
  → _is_general_question() check (may skip retrieval — see BUG-3)
  → detect_language() [disabled unless ENABLE_TRANSLATION=true]
  → vector_store.search(query, num_results=initial_k)   ← Qdrant call
  → retrieval_optimizer.optimize_retrieval(threshold=0.0) ← local, no API
    → filter_by_similarity [SKIPPED — see BUG-1]
    → rerank_by_relevance [runs, limited value]
    → deduplicate_documents [runs, helps]
    → select_top_k [runs]
  → ChatGroq(model=llama-3.3-70b-versatile).invoke(prompt)  ← Groq API call
  → SimpleMemory.update(session_id, ...)  ← unbounded growth
→ Response
```

### How retrieval_eval.py should bypass the API
```
Dataset query
→ vector_store.search(query, num_results=initial_k)   ← Qdrant, no LLM
→ retrieval_optimizer.optimize_retrieval(threshold=t)  ← local
→ [source_name for doc in result]                      ← extract PDF names
→ RAGEvaluator.evaluate_retrieval(sources, ground_truth) ← metrics
```

### RetrievalOptimizer internals
```python
def optimize_retrieval(documents, query, top_k, enable_dedup, enable_rerank, similarity_threshold):
    if similarity_threshold > 0:           # Step 1 — SKIPPED when threshold=0.0
        documents = filter_by_similarity(...)
    if enable_rerank and documents:        # Step 2 — always runs
        documents = rerank_by_relevance(method="combined")
        # rerank uses: 0.6*similarity + 0.4*keyword_overlap
        # keyword filter: only words with len > 3 (drops: CPU, RAM, AND, NOR, bit, bus)
    if enable_dedup and len(documents) > 1:  # Step 3 — always runs
        documents = deduplicate_documents(jaccard_threshold=0.85)
    return select_top_k(documents, k=top_k)  # Step 4 — always runs
```

---

## 8. Decisions Already Made (Do Not Re-Debate)

| Decision | Rationale |
|---|---|
| Keep Qdrant as vector store | Technology is not the bottleneck |
| Document-level ground truth for this phase | Run trusted baseline first, then chunk-level |
| Test both `threshold=0.0` AND `threshold=0.3` | Reveal the impact of the BUG-1 call site |
| TopK values: 3, 5, 10, 20 | Depth experiment to find precision/recall tradeoff |
| No LLM calls in retrieval eval | Groq rate limits kill full runs |
| No generation/faithfulness eval in this phase | Focus exclusively on retrieval |
| HitRate@1, @3, @5 as new metrics | Binary "did we find it?" complement to precision |
| Report mean + P95 retrieval latency | Understand latency cost of increasing K |

---

## 9. What the Next Agent Should Do — Exact Steps

### Step 1 — Verify environment (< 5 min)
```bash
cd "d:\College 🏛\Final Project\edumate\EduMate-RAG"
.venv311\Scripts\activate
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('QDRANT:', bool(os.getenv('QDRANT_URL')))"
# Should print: QDRANT: True
```

### Step 2 — Implement TASK A (metrics_calculator.py changes)
Read file first: `evaluation/metrics/metrics_calculator.py` (336 lines — read fully, it's small)  
Make targeted edits:
- Lines 24-34: Expand `RetrievalMetrics` dataclass
- Lines 95-137: `PrecisionRecallCalculator` — fix `recall_at_k` line 123-124
- Lines 162-211: After `NDCGCalculator`, insert `HitRateCalculator`
- Lines 214-240: Update `RAGEvaluator.__init__` and `evaluate_retrieval`

**Backward compat rule:** New fields in `RetrievalMetrics` must have `= 0.0` defaults. Old `run_evaluation.py` accesses `precision_at_3`, `precision_at_5`, `recall_at_5`, `mrr`, `ndcg_at_10` — keep these as required (no defaults).

### Step 3 — Create TASK B (retrieval_eval.py)
Create `evaluation/retrieval_eval.py` per the spec in Section 6.  
Key output structure:
```json
{
  "timestamp": "...",
  "ground_truth_granularity": "document",
  "thresholds_tested": [0.0, 0.3],
  "top_k_values_tested": [3, 5, 10, 20],
  "experiments": [
    {
      "config": {"threshold": 0.0, "top_k": 3, "initial_k": 10},
      "aggregate": {
        "num_queries": 85,
        "avg_latency_ms": ...,
        "p95_latency_ms": ...,
        "avg_precision_at_1": ...,
        "avg_precision_at_3": ...,
        "avg_precision_at_5": ...,
        "avg_precision_at_10": ...,
        "avg_recall_at_1": ...,
        "avg_recall_at_3": ...,
        "avg_recall_at_5": ...,
        "avg_recall_at_10": ...,
        "avg_mrr": ...,
        "avg_ndcg_at_5": ...,
        "avg_ndcg_at_10": ...,
        "avg_hit_rate_at_1": ...,
        "avg_hit_rate_at_3": ...,
        "avg_hit_rate_at_5": ...,
        "avg_hit_rate_at_10": ...
      },
      "per_query": [...]
    }
  ]
}
```

Console output must include:
- Threshold comparison table (threshold=0.0 vs 0.3 at fixed top_k=5)
- Depth experiment table (K=3,5,10,20 at each threshold)
- Best configuration recommendation

### Step 4 — Run TASK C
```bash
python evaluation/retrieval_eval.py
```
Expected: ~5-15 minutes (680 Qdrant queries, no LLM).  
Result file saved to: `evaluation/results/retrieval_eval_<timestamp>.json`

### Step 5 — Update this file
After completing tasks, update Section 6 to mark TASK A, B, C as ✅ COMPLETED and add the baseline metric values to Section 5.

---

## 10. Metrics Reference — Mathematical Definitions

All metrics are bounded ∈ [0, 1]. If any value exceeds this, there is a bug.

| Metric | Formula | Interpretation |
|---|---|---|
| **Precision@K** | `|relevant ∩ top_K| / K` | Fraction of top-K that are relevant |
| **Recall@K** | `|unique_relevant ∩ top_K| / |ground_truth|` | Fraction of GT found in top-K |
| **MRR** | `1 / rank_of_first_relevant` | 0 if nothing found |
| **NDCG@K** | `DCG@K / idealDCG@K` | Ranking quality accounting for position |
| **HitRate@K** | `1 if any(top_K) ∈ GT else 0` | Binary: did we find anything? |

**DCG formula used:** `Σ relevance_i / log2(i+1)` with `seen` set to avoid double-counting duplicates.  
**Ideal DCG:** Assumes all ground truth docs appear in positions 1..n_relevant.

**At document-level (current):** "relevant" = chunk's source PDF name matches ground truth PDF name.

---

## 11. Test Suite Quick Reference

```bash
# Run all unit tests (no API server needed, ChromaDB mocked)
pytest tests/unit/ -v

# Run with coverage (currently disabled in pytest.ini — uncomment if needed)
# pytest tests/unit/ --cov=src --cov-report=term-missing
```

**Test files and what they actually test:**

| File | Tests | Trustworthy? |
|---|---|---|
| `test_retrieval_optimizer.py` | 5 tests of actual RetrievalOptimizer | ✅ Yes |
| `test_key_rotation.py` | 4 tests of a **copy** of RAGChain logic | ⚠️ Misleading |
| `test_pdf_loader.py` | 4 tests of PDF loader | ✅ Yes |

**No tests exist for:** metric formulas, HitRate, session memory, general question detection, evaluate_generation.

---

## 12. Token-Saving Rules for Future Agents

1. **Do NOT read** `MASTER_PRESENTATION.md`, `HUGGING_FACE_DEPLOYMENT.md`, `README.md` — they contain no technical truth useful for implementation tasks.
2. **Do NOT re-read** `phase1_brutal_review.md` or `phase2_architecture_attack.md` — findings are summarized in Section 4 of this document.
3. **Do NOT read** `evaluation/results/*.json` files unless specifically asked to analyze results — they are large (up to 116KB) and stale.
4. **Always read this file first** before reading any source file. Most facts you need are already here.
5. **When editing `rag_chain.py`**, read only the specific method you need (line numbers are in Section 7). Do not read the full 418-line file unless the task requires it.
6. **`config.py` is 91 lines** — safe to read fully if needed. It validates at import time; remember this when writing test scripts.
7. **Run searches before reading files** — use `grep_search` to find specific patterns rather than reading entire large files.

---

## 13. Project Quality Honest Assessment (For Portfolio Context)

| Dimension | Honest Score | Main Issue |
|---|---|---|
| Architecture | 5/10 | Global singleton, dead code, sync routes |
| Retrieval Pipeline | 4/10 | Filtering disabled at call site |
| Evaluation | 9/10 | Clean retrieval baseline established (73 queries). Initial generation/faithfulness evaluation framework and baseline established (10 queries). |
| Testing | 4/10 | Key rotation tests test a copy |
| Scalability | 3/10 | P95 latency ~9s, sync routes, ~0.85 effective concurrent users |

**Actual Baseline Metrics (from June 12 ChromaDB Evaluation at top_k=5, threshold=0.0 on clean 73-query dataset):**
- Avg Precision@3: 0.7169
- Avg Precision@5: 0.6932
- Avg Recall@5: 0.7945
- Avg MRR: 0.7534
- Avg NDCG@10: 0.7642
- Avg HitRate@5: 0.7945
*(Note: Initial baseline run had 25/85 queries failing due to missing Operating Systems PDF and mismatched Data structure Book metadata. These have been cleaned and resolved via Option A.)*

**Actual Generation Metrics (from June 15 Llama 3.3 70B evaluation on 10-query easy stratum subset, top_k=5, threshold=0.0):**
- Mean Context Faithfulness (MCF): 0.5720
- Avg Source Accuracy: 1.0000
- Avg NLI Relevance: 0.7626
- Avg Groq Relevance: 0.9400
- Avg Groq Completeness: 0.8400
- Median Latency: 5443 ms
- P95 Latency: 9185 ms

---

*This document was written by Antigravity AI on 2026-06-12 after full codebase analysis across 3 conversation sessions. Update it whenever a task is completed.*

## 14. Backend Integration Update

### Implemented .NET integration endpoint

EduMate-RAG now exposes a stateless backend-facing endpoint:

```http
POST /api/integrations/query
```

Request shape:

```json
{
  "userId": "user-123",
  "conversationId": "conv-456",
  "message": "Explain instruction pipelining",
  "messages": [
    {
      "question": "What is CPU architecture?",
      "answer": "CPU architecture describes the structure and behavior of the processor."
    }
  ]
}
```

Response shape:

```json
{
  "userId": "user-123",
  "conversationId": "conv-456",
  "question": "Explain instruction pipelining",
  "answer": "...",
  "sources": ["computer Architecture Book.pdf"],
  "isGeneral": false,
  "latencyMs": 2410.7,
  "timingsMs": {}
}
```

Design decision:

- .NET owns users, conversations, message listing, deletion, and durable message storage.
- EduMate-RAG receives only request-scoped short-term context and does not persist integration conversations.
- `messages` contains previous Q&A pairs only, ordered oldest to newest.
- .NET should send only the latest 5 previous Q&A pairs.
- EduMate-RAG defensively caps received history to the latest 5 pairs.
- The existing `/api/query` endpoint remains for standalone/demo mode.

Code locations:

- `src/api/main.py`: integration request/response models and `/api/integrations/query`
- `src/core/rag_chain.py`: `query_with_history()` and request-scoped external history support
- `tests/verification/test_api.py`: integration endpoint tests
- `docs/EDUMATE_INTEGRATION.md` and `README.md`: updated contract docs

Verification:

```bash
.venv311\Scripts\python.exe -m pytest tests\verification\test_api.py -v
```

Result: 9 passed.
## 15. Continuation Instructions For Next Agent

### First Action

Read `AGENT_HANDOFF.md` completely before opening any source files.

Do not re-review old conversations.

This document is the source of truth.

---

### Current Objective

Continue from **Section 9 — What the Next Agent Should Do**.

Execute:

1. Step 1 — Environment Verification
2. Step 2 — TASK A (metrics_calculator.py)
3. Step 3 — TASK B (retrieval_eval.py)
4. Step 4 — TASK C (run retrieval evaluation)

Do not introduce new architecture changes before the baseline exists.

Do not modify the retrieval pipeline beyond what is required for the approved tasks.

---

### Scope Restrictions

Current phase is:

```text
Retrieval Evaluation Baseline
```

Focus only on:

* Retrieval metrics
* Evaluation correctness
* Retrieval experiments
* Result analysis

Ignore:

* CI/CD
* Airflow
* Dagster
* Prefect
* Terraform
* Monitoring
* Kubernetes
* Production deployment
* Authentication
* UI improvements

unless directly required for retrieval evaluation.

---

### After TASK C Completes

Before proposing any new retrieval improvements:

#### Validate Results

Confirm:

* Precision@K ∈ [0,1]
* Recall@K ∈ [0,1]
* MRR ∈ [0,1]
* NDCG@K ∈ [0,1]
* HitRate@K ∈ [0,1]

If any metric exceeds valid bounds:

* Stop
* Identify root cause
* Fix evaluation code
* Re-run evaluation

Do not trust invalid results.

---

### Required Post-Evaluation Analysis

Analyze:

#### Threshold Experiment

Compare:

* threshold = 0.0
* threshold = 0.3

Determine:

* precision impact
* recall impact
* latency impact

---

#### Retrieval Depth Experiment

Compare:

* K = 3
* K = 5
* K = 10
* K = 20

Determine:

* recall saturation point
* precision degradation
* latency cost

---

#### Failure Analysis

Identify:

* queries with HitRate@5 = 0
* queries with MRR = 0

For each failure:

* query
* ground truth document
* top retrieved documents
* likely root cause

Classify root cause as:

* chunking
* embeddings
* reranking
* retrieval depth
* dataset issue

---

#### Optimizer Assessment

Determine whether:

```text
Retriever + Optimizer
```

actually outperforms:

```text
Retriever Only
```

If not measured yet:

recommend the smallest possible experiment to measure it.

---

### README Update (After Baseline Exists)

Once retrieval evaluation is complete and validated:

Update README.md.

README should include:

* Project overview
* Current architecture
* Retrieval pipeline
* Technology stack
* Evaluation methodology
* Baseline retrieval metrics
* Known limitations
* Retrieval roadmap

Rules:

* Do not use obsolete evaluation numbers.
* Do not use metrics from old buggy result files.
* Do not exaggerate performance.
* Document only validated findings.

---

### Documentation Maintenance

After all tasks are complete:

Update `AGENT_HANDOFF.md`.

#### Section 5 — Evaluation History

Add:

* new result filename(s)
* date
* query count
* trust status
* key observations

---

#### Section 6 — Phase Status

Move completed items from:

```text
🔄 DECIDED BUT NOT IMPLEMENTED
```

to:

```text
✅ COMPLETED
```

for:

* TASK A
* TASK B
* TASK C

if successfully finished.

Add:

```text
🔄 TASK D — README Refresh
```

and mark complete if README was updated.

---

#### Section 13 — Honest Assessment

Re-evaluate scores using actual baseline results.

Do not leave placeholder scores if evidence now exists.

---

### Deliverables Before Ending Session

Provide:

1. Retrieval evaluation summary
2. Best configuration recommendation
3. Failure analysis summary
4. Optimizer impact assessment
5. Updated README.md
6. Updated AGENT_HANDOFF.md

The project should leave the session with a trusted retrieval baseline and synchronized documentation.
