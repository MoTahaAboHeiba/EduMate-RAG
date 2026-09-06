# EduMate RAG System

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: App Integration Ready](https://img.shields.io/badge/Status-App%20Integration%20Ready-brightgreen.svg)](#)

A Retrieval-Augmented Generation (RAG) service for EduMate. It can run behind the main EduMate .NET backend for the Flutter app, or as a standalone FastAPI service for demos and local testing. Powered by FastAPI, LangChain, Qdrant/ChromaDB, and Groq LLM inference.

---

## Table of Contents

- [Overview](#overview)
- [Operating Modes](#operating-modes)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [How RAG Works](#how-rag-works)
- [Troubleshooting](#troubleshooting)
- [Performance Metrics](#performance-metrics)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**EduMate RAG** is a conversational question-answering service for university course materials. It retrieves relevant chunks from indexed PDFs, sends the retrieved context to an LLM, and returns an answer with source attribution.

### Key Innovation
Answers are grounded in indexed course PDFs and returned with source document names. In the integrated app flow, conversation history is owned by the .NET backend and sent to RAG as a short request-scoped context window.

---

## Operating Modes

| Mode | Caller | Conversation Owner | Main Endpoint | Use Case |
|---|---|---|---|---|
| **EduMate App Integration** | .NET backend | .NET backend database | `POST /api/integrations/query` | Real Flutter app flow |
| **Standalone Service** | Flutter, Swagger, or local client | EduMate-RAG local session memory/files | `POST /api/query` | Demo, testing, local development |

Flutter should call the .NET backend only. It owns users, auth, and conversation storage, then calls EduMate-RAG when it needs an answer (sending the current question plus the latest 5 Q&A pairs). Running standalone, clients manage state themselves via `X-Session-Token` and the built-in conversation endpoints.

---

## Features

- **PDF-Based Q&A**: answers only from indexed course materials
- **Multi-Turn Conversations**: remembers context across questions
- **Semantic Retrieval**: Qdrant Cloud or local ChromaDB
- **AI-Powered Generation**: Groq's `openai/gpt-oss-120b`
- **Multilingual**: handles Arabic and English
- **Source Attribution**: every answer cites its source document
- **Zero-Cost Inference**: runs on Groq's free tier
- **Incremental Indexing**: file change detection, embedding cache, parallel PDF processing

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Language | Python 3.11 | Core application |
| Web Framework | FastAPI 0.109+ | REST API server |
| LLM Framework | LangChain 0.1.20+ | RAG orchestration |
| LLM Provider | Groq (`openai/gpt-oss-120b`) | Answer generation |
| Vector DB | Qdrant Cloud / ChromaDB | Semantic search |
| PDF Processing | PyPDF 4.0.1+ | Text extraction |
| Config | python-dotenv | Environment variables |

---

## Architecture

Flutter talks to the .NET backend, which owns user/conversation data and calls EduMate-RAG only for AI answers. In standalone mode, clients can call EduMate-RAG directly.

```
                 Flutter Mobile App
                        │ HTTP/REST
                        ▼
           FastAPI Server (Port 8000)
        POST /api/query · POST /api/index
                        │
                        ▼
             RAG Pipeline (LangChain)
              ┌─────────┴─────────┐
              ▼                   ▼
      Local ChromaDB        Qdrant Cloud
     (dev, ONNX embed.)    (prod, HTTPS)
              └─────────┬─────────┘
                        ▼
              Groq API (LLM Inference)
               openai/gpt-oss-120b
```

---

## Installation

```bash
# 1. Clone
git clone https://github.com/MoTahaAboHeiba/EduMate-RAG.git
cd EduMate-RAG

# 2. Virtual environment
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env         # then add your GROQ_API_KEY

# 5. Add PDFs to assets/course_pdfs/

# 6. Verify setup
python test_groq_direct.py

# 7. Run + index
python main.py
curl -X POST http://localhost:8000/api/index
```

**Prerequisites:** Python 3.9+, Git, 4GB+ RAM, a free [Groq API key](https://console.groq.com), and your course PDFs.

---

## Configuration

```bash
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.3-70b-versatile      # recommended

CHROMA_DB_PATH=/tmp/edumate/chroma_db
CONVERSATION_DIR=/tmp/edumate/conversations
PDF_FOLDER_PATH=./assets/course_pdfs

API_HOST=localhost
API_PORT=8000
DEBUG=True
ADMIN_KEY=change-this-admin-key
```

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-8b-instant` | Very Fast | Good | Budget/Speed |
| `llama-3.3-70b-versatile` | Medium | Excellent | **Recommended** |
| `llama-2-70b-4096` | Fast | Great | Alternative |

---

## Usage

```bash
# Start server
python main.py

# Index PDFs
curl -X POST http://localhost:8000/api/index

# Ask a question
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a prerequisite?"}'

# Follow-up (system remembers!)
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me more about that"}'
```

Interactive testing available at `http://localhost:8000/docs`.

---

## API Documentation

Base URL: `http://localhost:8000`

| Endpoint | Purpose |
|---|---|
| `GET /` | Health check / API info |
| `GET /health` | System + vector store status |
| `POST /api/integrations/query` | .NET backend → RAG query (app flow) |
| `POST /api/query` | Standalone query with conversation memory |
| `POST /api/index` | Index PDFs (`incremental`, `force_full` params) |
| `GET /api/cache/stats` | Embedding/file-tracking cache stats |
| `POST /api/cache/clear` | Reset embedding cache / file tracking |
| `GET /api/conversation/history` | Retrieve conversation history |
| `POST /api/conversation/clear` | Start a fresh conversation |
| `GET /api/conversation/info` | Conversation turn/message counts |

### `POST /api/integrations/query` contract

```json
{
  "userId": "user-123",
  "conversationId": "conv-456",
  "message": "Explain instruction pipelining",
  "messages": [
    {"question": "What is CPU architecture?", "answer": "..."}
  ]
}
```

- `message` is the current question; `messages` holds prior Q&A pairs only, oldest → newest.
- Send at most the latest 5 pairs (RAG caps to 5 defensively either way).
- The .NET backend should save `question`, `answer`, and `sources` after each response.

### Users & Sessions (standalone mode)

Include a stable `X-Session-Token` header per user/device. Conversations are isolated by token, and sharing a token means sharing history.

---

## Project Structure

```
EduMate-RAG/
├── main.py                  # Entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py
│   ├── document_processing/  # PDF loading, vector store, caching
│   ├── core/                 # RAG pipeline + retrieval optimizer
│   └── api/                  # FastAPI endpoints
├── assets/
│   ├── course_pdfs/
│   └── chroma_db/
└── tests/
```

---

## Documentation

- [Quick Start Guide](./docs/QUICKSTART_UI.md)
- [Project Structure](./docs/PROJECT_STRUCTURE.md)
- [Flutter Integration](./docs/EDUMATE_INTEGRATION.md)
- [Users & Conversations](./docs/EDUMATE_USERS_AND_CONVERSATIONS.md)
- [Optimization Summary](./OPTIMIZATION_SUMMARY.md)
- [Qdrant Migration](./docs/QDRANT_MIGRATION.md)
- [Testing Guide](./docs/TESTING.md)

---

## How RAG Works

1. **Retrieval**: embed the question, find the top-K similar PDF chunks.
2. **Context Creation**: combine retrieved chunks with source labels.
3. **Generation**: send context plus question to Groq's Llama 3.3 70B for the final answer.

Conversation memory feeds prior turns back into retrieval and generation, so the system understands follow-ups like "tell me more."

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `GROQ_API_KEY not set` | Check `.env` exists, key isn't the placeholder, no extra spaces, restart server |
| No PDFs found | Confirm files are in `assets/course_pdfs/` with lowercase `.pdf` extension |
| ChromaDB error | `rm -rf assets/chroma_db`, restart, re-index |
| Connection refused | Confirm `python main.py` is running; try a different `API_PORT` |
| Slow responses | Normal for large PDFs or first query; otherwise check network |

---

## Performance Metrics

Evaluated offline against 73 curated QA pairs (584 queries) across a 2×4 grid of similarity thresholds and Top-K depths, bypassing the LLM to isolate retrieval quality.

- **Best config (Top-K=20, threshold=0.0):** Precision@5 ≈ 0.73, Recall@10 ≈ 0.86, MRR ≈ 0.80
- **RetrievalOptimizer uplift (Top-K=5):** Precision@3 +5.2pts, Recall@5 +3.4pts, MRR +1.2pts over raw retrieval
- **Indexing:** ~18–20 chunks/sec (local ONNX embeddings, CPU)
- **Search latency:** <10ms (local ChromaDB) · ~200ms (Qdrant Cloud roundtrip)
- **Embeddings:** `all-MiniLM-L6-v2`, 384 dimensions

See `evaluation/retrieval_eval.py` and `PHASE5_EVALUATION_REPORT.md` for full results.

---

## Security Considerations

- Secrets in `.env`, never committed to Git
- Input validation on all endpoints
- No authentication or rate limiting yet. Add both before production.

---

## Contributing

1. Fork the repository
2. `git checkout -b feature/amazing-feature`
3. `git commit -m "Add amazing feature"`
4. `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

MIT. See [LICENSE](LICENSE).

---

Last updated: December 3, 2025
