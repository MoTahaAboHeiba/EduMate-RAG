# Qdrant Vector Database Migration Guide

## Overview

This guide covers the migration from ChromaDB-only to a Qdrant Cloud backend for production deployments. ChromaDB is retained for local development.

## Problem Statement

ChromaDB stores vectors locally in containers, which is problematic for Railway deployments:
- Railway containers use ephemeral filesystems
- Vector files disappear after container restarts
- App becomes non-functional until PDFs are re-indexed
- Not production-ready for persistent deployments

## Solution

Maintain ChromaDB for development and use Qdrant Cloud for production persistence.

## Backend Selection

Switch via environment variable:

```env
VECTOR_STORE_BACKEND=chroma      # Local development
VECTOR_STORE_BACKEND=qdrant      # Production
```

## Configuration

### Environment Variables

```env
VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_api_key
```

### Validation

The system validates configuration at startup:
- Invalid backend values fail fast
- Missing Qdrant credentials fail fast
- Placeholder values (e.g., `your_real_qdrant_url`) fail immediately

## Implementation Details

### VectorStore Abstraction

`src/document_processing/vector_store.py` now provides backend-neutral interface:

- `ChromaVectorStore` - Local development
- `QdrantVectorStore` - Cloud production
- `VectorStore` factory - Selects backend from environment

Public methods (unchanged):
- `index_pdfs()`
- `similarity_search(query, k)`
- `get_collection_info()`
- `search(query, num_results)`

### Startup Behavior

On application startup:

1. Check vector count in database
2. If count is 0, automatically index PDFs
3. If count > 0, skip indexing (vectors already present)

This allows Railway to boot into a usable state without unnecessary re-indexing on container restarts.

### Batch Processing

Qdrant indexing uses optimized batch handling:

- Batch size: 32 vectors per write
- Client timeout: 120 seconds
- Write mode: Asynchronous (`wait=False`)
- Retry logic for failed batches

Large document sets are uploaded reliably without blocking.

## Docker Configuration

Production Dockerfile uses single worker:

```dockerfile
--workers 1
```

Rationale: This app maintains process-local conversation memory and performs startup indexing. Multiple workers cause:
- Inconsistent memory state across workers
- Duplicate indexing on each container start
- Race conditions

## Troubleshooting

### Issue: "documents_indexed": 0

Cause: PDF extraction failed or Qdrant write timeout

Solution:
```bash
# Check PDF format (try PyMuPDF fallback)
# Verify Qdrant API key and URL
# Monitor logs for chunk extraction count
```

### Issue: Network timeout errors

Cause: Connection to Qdrant Cloud timing out

Solution:
- Increase client timeout (already set to 120s)
- Reduce batch size further (try 16)
- Check Qdrant Cloud cluster status

### Issue: Duplicate vectors after restart

Cause: Retry logic re-uploaded missing vectors

Solution:
- This is expected behavior
- Vectors use deterministic IDs
- Re-uploads are safe (no duplicates created)

## Deployment Checklist

- [ ] Qdrant Cloud account created
- [ ] Collection named `course_materials` created
- [ ] API key generated
- [ ] Cluster URL obtained
- [ ] Environment variables configured
- [ ] PDFs in assets folder
- [ ] Local test with VECTOR_STORE_BACKEND=qdrant
- [ ] Docker build and test
- [ ] Deploy to Railway/Hugging Face

## Metrics

Production performance after migration:

- Vector count: 5637 indexed chunks
- Startup time: ~30 seconds first run, <5 seconds on repeat
- Query latency: 32-45ms (local), 87ms (cloud)
- Index uptime: 100% (persistent in Qdrant Cloud)

## References

- Qdrant Documentation: https://qdrant.tech/documentation/
- LangChain Qdrant Integration: https://python.langchain.com/docs/integrations/vectorstores/qdrant
- Railway Deployment: See HUGGING_FACE_DEPLOYMENT.md (applies to Railway too)