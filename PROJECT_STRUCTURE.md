# EduMate RAG - Project Structure Guide

## Overview

The EduMate RAG project has been reorganized into a **feature-based architecture** for better maintainability, scalability, and clarity. This guide explains the new structure and how to navigate it.

## Directory Structure

```
EduMate-RAG/
├── src/
│   ├── core/                      # RAG Pipeline & Optimization
│   │   ├── rag_chain.py           # Main RAG chain with memory
│   │   ├── retrieval_optimizer.py # Document filtering & reranking
│   │   └── __init__.py
│   │
│   ├── document_processing/       # PDF & Vector Store
│   │   ├── pdf_loader.py          # PDF extraction & chunking
│   │   ├── vector_store.py        # ChromaDB & Qdrant backends
│   │   └── __init__.py
│   │
│   ├── conversation/              # Conversation Management
│   │   ├── conversation_manager.py # Store & retrieve conversations
│   │   └── __init__.py
│   │
│   ├── config/                    # Configuration
│   │   ├── config.py              # App configuration & validation
│   │   └── __init__.py
│   │
│   ├── api/                       # FastAPI Application
│   │   ├── main.py                # API endpoints & server
│   │   ├── static/                # UI files
│   │   └── __init__.py
│   │
│   ├── utils/                     # Shared Utilities
│   │   └── __init__.py
│   │
│   ├── __init__.py
│   │
│   # Backward-compatible imports (for migration)
│   ├── config.py                  # → src/config/config.py
│   ├── rag_chain.py               # → src/core/rag_chain.py
│   ├── retrieval_optimizer.py     # → src/core/retrieval_optimizer.py
│   ├── pdf_loader.py              # → src/document_processing/pdf_loader.py
│   ├── vector_store.py            # → src/document_processing/vector_store.py
│   └── conversation_manager.py    # → src/conversation/conversation_manager.py
│
├── tests/
│   ├── unit/                      # Unit Tests
│   │   ├── test_rag_chain.py
│   │   ├── test_vector_store.py
│   │   └── __init__.py
│   │
│   ├── integration/               # Integration Tests
│   │   ├── test_groq_direct.py
│   │   ├── test_suite_final.py
│   │   └── __init__.py
│   │
│   ├── verification/              # Verification Scripts
│   │   ├── verify_chromadb.py
│   │   └── __init__.py
│   │
│   └── __init__.py
│
├── scripts/                       # Utility Scripts
│   ├── count_chunks.py
│   ├── run_tests.py
│   └── verify_chromadb.py
│
├── docs/                          # Documentation
├── evaluation/                    # Evaluation Reports
├── assets/
│   ├── course_pdfs/               # PDF documents
│   ├── chroma_db/                 # Vector database
│   └── conversations/             # Conversation history
│
├── requirements.txt               # Python dependencies
├── requirements-test.txt          # Test dependencies
├── pytest.ini                     # Pytest configuration
├── Dockerfile                     # Docker image
├── .env.example                   # Environment template
└── README.md                      # Main documentation
```

## Module Guide

### 1. **src/core/** - RAG Pipeline
The heart of the system - handles question answering and document retrieval optimization.

- **rag_chain.py**: Main RAG chain that orchestrates retrieval, generation, and conversation memory
  - `RAGChain`: Multi-turn conversation pipeline
  - `LanguageHelper`: Language detection and translation
  - `SimpleMemory`: In-memory conversation buffer

- **retrieval_optimizer.py**: Advanced document filtering and ranking
  - Similarity filtering
  - Relevance-based reranking
  - Deduplication
  - Top-K selection

### 2. **src/document_processing/** - Data Ingestion
Handles PDF extraction and vector embeddings.

- **pdf_loader.py**: Extracts text from PDFs and chunks it
  - Supports pypdf and PyMuPDF fallback
  - Configurable chunk sizes and overlaps
  - Metadata tracking

- **vector_store.py**: Vector database abstraction layer
  - ChromaDB backend (development)
  - Qdrant backend (production)
  - Unified search interface

### 3. **src/conversation/** - Conversation History
Manages persistent conversation storage per user session.

- **conversation_manager.py**: File-based conversation storage
  - Session isolation
  - Create, load, delete conversations
  - Multi-turn history tracking

### 4. **src/config/** - Configuration
Centralized configuration management.

- **config.py**: App configuration with validation
  - Groq API settings
  - Vector store backend selection
  - PDF processing parameters
  - LLM optimization tuning

### 5. **src/api/** - Web Server
FastAPI application exposing RAG functionality.

- **main.py**: REST API endpoints
  - `/api/query` - Ask questions
  - `/api/conversation/*` - Manage conversations
  - `/api/index` - Re-index PDFs
  - `/health` - Health check

## Backward Compatibility

The old import paths still work via compatibility imports in `src/`:

```python
# Old way (still works)
from src.config import config
from src.rag_chain import rag_chain

# New way (preferred)
from src.config.config import config
from src.core.rag_chain import rag_chain
```

## Migration Guide

If you have existing code using the old structure:

1. **Option A (Minimal change)**: No action needed - backward-compatible imports work
2. **Option B (Recommended)**: Update imports to new paths
   ```python
   # Before
   from src.vector_store import vector_store
   
   # After
   from src.document_processing.vector_store import vector_store
   ```

## Common Development Tasks

### Running the API
```bash
python -m uvicorn src.api.main:app --reload
```

### Running Tests
```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=src tests/
```

### Adding a New Feature

1. **Create new module**: Choose appropriate location
   - Core RAG logic → `src/core/`
   - Data processing → `src/document_processing/`
   - User-facing API → `src/api/main.py`

2. **Write tests**: Place in `tests/unit/` or `tests/integration/`

3. **Update imports**: Use full paths from module location

### Indexing Documents
```bash
# Via API
curl -X POST http://localhost:8000/api/index \
  -H "X-Admin-Key: your_admin_key"

# Programmatically
from src.document_processing.vector_store import vector_store
vector_store.index_pdfs()
```

## Key Design Decisions

1. **Feature-based Organization**: Grouped by business capability (not by technical layer)
2. **Backward Compatibility**: Old imports still work during transition
3. **Session Isolation**: Each user gets their own conversation memory
4. **Backend Abstraction**: Pluggable vector store (ChromaDB/Qdrant)
5. **Configuration Centralization**: Single source of truth for settings

## Dependencies by Module

| Module | Main Dependencies |
|--------|------------------|
| core/ | langchain, googletrans |
| document_processing/ | chromadb/qdrant, pypdf, PyMuPDF |
| conversation/ | (stdlib only) |
| config/ | python-dotenv |
| api/ | fastapi, uvicorn |

## Future Improvements

- [ ] Add caching layer for frequently accessed documents
- [ ] Implement conversation analytics
- [ ] Add multi-language support optimization
- [ ] Create admin dashboard
- [ ] Add streaming responses for long answers
- [ ] Implement session persistence across deployments

## Support

For questions about the new structure, see the individual module docstrings or check the test files for usage examples.
