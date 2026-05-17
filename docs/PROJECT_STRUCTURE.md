# EduMate RAG - Project Structure

This document describes the organized project structure for EduMate RAG.

##  Directory Structure

```
EduMate-RAG/

  main.py                          # Main entry point - Start the server here
  .env.example                     # Environment template
  .env                             # Your secrets (NOT in Git)
  .gitignore                       # Git ignore rules
  requirements.txt                 # Python dependencies
  requirements-test.txt            # Test dependencies
  pytest.ini                       # Pytest configuration

  docs/                            #  Documentation
    README.md                       # Main documentation
    QUICKSTART_UI.md               # Quick start guide
    UI_SETUP.md                    # UI setup instructions
    TESTING.md                     # Testing guide
    EDUMATE_INTEGRATION.md         # Flutter integration guide
    EDUMATE_USERS_AND_CONVERSATIONS.md  # Multi-user documentation
    PROJECT_STRUCTURE.md           # This file

  src/                            #  Source Code
    __init__.py
    config.py                      # Configuration management
    conversation_manager.py        # Conversation persistence
    pdf_loader.py                  # PDF processing
    rag_chain.py                   # RAG pipeline & LLM calls
    vector_store.py                # ChromaDB wrapper
    api/                           # FastAPI server
        __init__.py
        main.py                    # API endpoints
        static/                    # Frontend (HTML/CSS/JS)
            index.html

  tests/                          #  Tests
    __init__.py
    test_suite_final.py           # Main test suite
    integration/                   # Integration tests
        test_groq_direct.py       # Groq LLM testing
        verify_chromadb.py        # ChromaDB verification

  scripts/                        #  Utility Scripts
    count_chunks.py               # Count vectors in ChromaDB
    verify_chromadb.py            # Verify ChromaDB health
    run_tests.py                  # Test runner

  assets/                         #  Data Storage
    chroma_db/                    # ChromaDB vector database
       chroma.sqlite3            # Database file
    conversations/                # Saved conversations (by session)
       <session-token-1>/
          conv_*.json           # Conversation files
       <session-token-2>/
       ...
    course_pdfs/                  # Your PDF files
        Course_1.pdf
        Course_2.pdf
        ...

  htmlcov/                        # Test coverage reports
  .benchmarks/                    # Performance benchmarks
  venv/                           # Virtual environment (not in Git)
```

##  Where to Find Things

###  Running the Application
```bash
python main.py
```
Then open `http://localhost:8000`

###  Documentation
- **Getting Started**: See `docs/README.md`
- **Flutter Integration**: See `docs/EDUMATE_INTEGRATION.md`
- **Multi-user Support**: See `docs/EDUMATE_USERS_AND_CONVERSATIONS.md`
- **Testing**: See `docs/TESTING.md`
- **UI Setup**: See `docs/UI_SETUP.md`

###  Running Tests
```bash
# Run all tests
python scripts/run_tests.py

# Run integration tests only
python scripts/run_tests.py --integration

# Run with coverage
python scripts/run_tests.py --coverage
```

###  Utility Scripts
```bash
# Count chunks in ChromaDB
python scripts/count_chunks.py

# Verify ChromaDB health
python scripts/verify_chromadb.py

# Check Groq connection
python tests/integration/test_groq_direct.py
```

##  Source Code Organization

### `src/config.py`
- Loads environment variables
- Manages API keys and settings
- Centralized configuration

### `src/vector_store.py`
- ChromaDB wrapper
- PDF indexing
- Semantic search

### `src/pdf_loader.py`
- PDF text extraction
- Document chunking
- Page metadata

### `src/rag_chain.py`
- RAG pipeline orchestration
- Question-answer generation
- Conversation memory management
- Multi-language support (Arabic/English)
- Per-session token isolation

### `src/conversation_manager.py`
- Saves conversations to disk (JSON)
- Per-session storage (isolated by token)
- Conversation history retrieval
- Conversation deletion

### `src/api/main.py`
- FastAPI application definition
- All REST endpoints
- Request/response models
- Session token handling

### `src/api/static/index.html`
- Web UI for testing
- Chat interface
- Conversation management UI
- Session token generation

##  Data Flow

```
User Query
    ↓
[/api/query endpoint] (src/api/main.py)
    ↓
[RAG Chain] (src/rag_chain.py)
    → Detect Language (Arabic/English)
    → Retrieve Documents (src/vector_store.py)
    → Generate Answer (Groq LLM)
    → Translate if needed
    ↓
[Save to Conversation] (src/conversation_manager.py)
    ↓
Response to User
```

##  Session & User Isolation

- Each user gets a unique `X-Session-Token` header
- Conversations are stored under `assets/conversations/<session-token>/`
- In-memory conversation memory is also isolated per token
- Multiple users can use the backend simultaneously

##  Security Notes

- `.env` file contains secrets (never commit)
- Use `.env.example` as template
- Groq API key must be environment variable
- Session tokens should be unique per user/device

##  Performance Notes

- ChromaDB indices are cached in memory for speed
- PDF indexing happens once at startup
- Conversation memory is ephemeral (resets if server restarts)
- Conversations are persisted in JSON files on disk

##  Cleanup & Maintenance

- Delete `assets/conversations/<session-token>/` to remove session data
- Delete `assets/chroma_db/` to reset vector database
- Clear `htmlcov/` when regenerating coverage reports
- Run `scripts/count_chunks.py` periodically to verify indexing

##  Checklist for New Developers

- [ ] Read `docs/README.md`
- [ ] Copy `.env.example` to `.env` with your Groq API key
- [ ] Run `python main.py`
- [ ] Visit `http://localhost:8000`
- [ ] Read `docs/EDUMATE_INTEGRATION.md` if integrating with Flutter
- [ ] Run tests: `python scripts/run_tests.py`
- [ ] Check ChromaDB: `python scripts/verify_chromadb.py`
