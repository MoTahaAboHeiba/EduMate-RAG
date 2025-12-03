# 🎓 EduMate RAG System

A production-ready **Retrieval-Augmented Generation (RAG)** backend for the EduMate Flutter application. Powered by LangChain, ChromaDB, and Groq's free LLM API.

---

## 📖 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [How RAG Works](#how-rag-works)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

EduMate RAG is an intelligent question-answering system designed for Egyptian universities. It allows students to ask questions about their course materials, and the system retrieves relevant information from indexed PDFs and generates accurate answers using AI.

**Key Innovation:** Answers are grounded in your course materials only—no hallucinations, only facts from your PDFs.

---

## Features

- **📚 PDF-Based Q&A** - Answer questions only from indexed course materials
- **🚀 Fast Retrieval** - ChromaDB enables instant semantic search across documents
- **🤖 AI-Powered** - Groq's Llama 3.3 70B for high-quality answer generation
- **🌍 Multilingual** - Supports Arabic and English questions and documents
- **📊 Source Attribution** - Every answer includes the source documents
- **🔐 Secure** - Secrets stored in `.env`, never committed to Git
- **⚡ Free** - Uses free tier of Groq (no cost for inference)
- **📱 API-Ready** - RESTful endpoints for Flutter integration
- **📈 Production-Ready** - Professional code structure, error handling, logging

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Language** | Python 3.9+ | Core application |
| **Web Framework** | FastAPI | REST API server |
| **Web Server** | Uvicorn | ASGI server for FastAPI |
| **LLM Framework** | LangChain | RAG pipeline orchestration |
| **LLM Provider** | Groq | Free cloud LLM API |
| **LLM Model** | Llama 3.3 70B | Answer generation model |
| **Vector Database** | ChromaDB | Semantic search & embeddings |
| **PDF Processing** | PyPDF | Extract text from PDFs |
| **Configuration** | python-dotenv | Environment variables |
| **Version Control** | Git | Code versioning |

---

## Prerequisites

- **Python 3.9 or higher** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/)
- **Groq API Key** - Free from [Groq Console](https://console.groq.com)
- **Course PDFs** - Your course materials in PDF format
- **~2GB Storage** - For dependencies and vector database

**System Requirements:**
- RAM: Minimum 4GB (8GB recommended)
- Storage: 5GB+ free space
- Internet: Required for Groq API calls

---

## Installation

### **Step 1: Clone Repository**

git clone <your-repository-url>
cd EduMate-RAG

### **Step 2: Create Virtual Environment**

**Windows:**
python -m venv venv
venv\Scripts\activate

**macOS/Linux:**
python -m venv venv
source venv/bin/activate

### **Step 3: Install Dependencies**

pip install -r requirements.txt

### **Step 4: Configure Environment**

1. Copy the example file:
cp .env.example .env

2. Edit `.env` and add your Groq API key:
# Open .env in your text editor and add:
GROQ_API_KEY=gsk_your_actual_key_here

### **Step 5: Add Course PDFs**

Place your course PDF files in:
assets/course_pdfs/
├── course_1.pdf
├── course_2.pdf
└── ...

### **Step 6: Verify Installation**

python test_groq_direct.py

Expected output:
🔄 Testing Groq connection...
✅ Groq is working!
Response: content='...'

---

## Configuration

### **.env File**

Edit `.env` with your settings:

# Groq API Configuration
GROQ_API_KEY=gsk_your_key_here              # Your Groq API key (from console.groq.com)
GROQ_MODEL=llama-3.3-70b-versatile          # LLM model to use

# ChromaDB Configuration
CHROMA_DB_PATH=./assets/chroma_db           # Where vector DB is stored

# API Configuration
API_HOST=localhost                           # API host
API_PORT=8000                               # API port
DEBUG=True                                  # Enable debug logging

# PDF Configuration
PDF_FOLDER_PATH=./assets/course_pdfs        # Where to find PDFs

### **Get Groq API Key**

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up (free)
3. Navigate to "API Keys"
4. Create new API key
5. Copy and paste into `.env`

### **Available Groq Models**

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-8b-instant` | ⭐⭐⭐⭐⭐ Fastest | ⭐⭐⭐ Good | Budget/Speed |
| `llama-3.3-70b-versatile` | ⭐⭐⭐ Medium | ⭐⭐⭐⭐⭐ Best | **Recommended** |
| `llama-2-70b-4096` | ⭐⭐⭐⭐ Fast | ⭐⭐⭐⭐ Great | Alternative |

---

## 📖 Usage

### **Start the Server**

python main.py

Expected output:
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete

### **Index Your PDFs**

In a new terminal:

curl -X POST http://localhost:8000/api/index

Response:
{
  "status": "success",
  "message": "PDFs indexed successfully",
  "documents_indexed": 45
}

Server output:
🔄 Starting PDF indexing...
📚 Found 2 PDF(s)
📖 Processing: course_1.pdf
   ✅ Extracted 23 chunks
📖 Processing: course_2.pdf
   ✅ Extracted 22 chunks
✅ Indexing complete! Total documents: 45

### **Query the System**

**Using FastAPI Docs (Easiest):**

1. Open browser: `http://localhost:8000/docs`
2. Find **POST /api/query**
3. Click "Try it out"
4. Enter question:
{
  "question": "What are the prerequisites for English Language 2?"
}
5. Click "Execute"

**Using curl:**

curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is a prerequisite?"}'

**Response:**

{
  "question": "What is a prerequisite?",
  "answer": "Based on the course materials, a prerequisite is a course or requirement that must be completed before enrolling in a specific course...",
  "sources": ["Computer Science -English 2- First Year 2023"],
  "num_context_docs": 3
}

### **Check System Health**

curl http://localhost:8000/health

Response:
{
  "status": "healthy",
  "model": "llama-3.3-70b-versatile",
  "vector_store": {
    "collection": "course_materials",
    "documents_indexed": 45
  }
}

---

## API Documentation

### **Base URL**
http://localhost:8000

### **Endpoints**

#### **1. GET /**
Root endpoint

**Request:**
curl http://localhost:8000/

**Response:**
{
  "message": "EduMate RAG API is running!",
  "version": "1.0.0"
}

---

#### **2. GET /health**
Health check - returns server status

**Request:**
curl http://localhost:8000/health

**Response:**
{
  "status": "healthy",
  "model": "llama-3.3-70b-versatile",
  "vector_store": {
    "collection": "course_materials",
    "documents_indexed": 45
  }
}

---

#### **3. POST /api/index**
Index all PDFs into the vector database

**Request:**
curl -X POST http://localhost:8000/api/index

**Response:**
{
  "status": "success",
  "message": "PDFs indexed successfully",
  "documents_indexed": 45
}

**Returns:**
- `status` - "success" or "error"
- `message` - Human readable message
- `documents_indexed` - Number of chunks created

---

#### **4. POST /api/query**
Query the RAG system with a question

**Request:**
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the prerequisite for CS101?"
  }'

**Request Body:**
{
  "question": "Your question here"
}

**Response:**
{
  "question": "What is the prerequisite for CS101?",
  "answer": "Based on the course materials, the prerequisite for CS101 is...",
  "sources": ["Computer Science - First Year 2023"],
  "num_context_docs": 3
}

**Returns:**
- `question` - The student's question
- `answer` - AI-generated answer from PDFs
- `sources` - List of PDF sources used
- `num_context_docs` - Number of relevant documents retrieved

---

### **Error Handling**

**400 - Bad Request:**
{
  "detail": "Question cannot be empty"
}

**500 - Server Error:**
{
  "detail": "Error processing query: [error details]"
}

---

## Project Structure

EduMate-RAG/
│
├── 📄 main.py                    # Entry point - starts the server
├── 📄 requirements.txt            # Python dependencies
├── 📄 README.md                  # This file
├── 📄 .env.example               # Template for environment variables
├── 📄 .env                       # Your actual secrets (NOT in Git)
├── 📄 .gitignore                 # Git ignore rules
│
├── 📁 src/                       # Source code
│   ├── 📄 __init__.py
│   ├── 📄 config.py              # Configuration loader
│   ├── 📄 pdf_loader.py          # PDF extraction & chunking
│   ├── 📄 vector_store.py        # ChromaDB integration
│   ├── 📄 rag_chain.py           # RAG pipeline
│   └── 📁 api/
│       ├── 📄 __init__.py
│       └── 📄 main.py            # FastAPI endpoints
│
├── 📁 assets/                    # Data & storage
│   ├── 📁 course_pdfs/           # Your course PDF files
│   └── 📁 chroma_db/             # Vector database (auto-created)
│
├── 📁 tests/                     # Test files
│   ├── 📄 __init__.py
│   ├── 📄 test_groq_direct.py    # Test Groq connection
│   └── 📄 test_embeddings.py     # Test embeddings
│
└── 📁 venv/                      # Python virtual environment
    ├── 📁 Scripts/ (Windows) or bin/ (macOS/Linux)
    ├── 📁 Lib/
    └── ...

---

## How RAG Works

### **RAG = Retrieval-Augmented Generation**

RAG is a 3-step process:

#### **Step 1: Retrieval**
Student Question: "What is a prerequisite?"
        ↓
Search ChromaDB with embeddings
        ↓
Find relevant PDF chunks (top 3)

#### **Step 2: Context Creation**
Combine retrieved chunks:
"[Computer Science PDF] A prerequisite is a course..."
"[English PDF] Prerequisites are requirements..."
"[Admin PDF] Must complete prerequisites before..."

#### **Step 3: Generation**
Send to Groq LLM:
Context: [above]
Question: "What is a prerequisite?"
        ↓
LLM generates answer based on context
        ↓
"Based on the course materials, a prerequisite is..."

### **Data Flow Diagram**

Student Question
        ↓
[1. RETRIEVAL - ChromaDB]
        ├─ Search using embeddings
        ├─ Find relevant PDF chunks
        └─ Return top 3 matches
        ↓
[2. CONTEXT CREATION]
        ├─ Combine chunks
        ├─ Add metadata
        └─ Format for LLM
        ↓
[3. GENERATION - Groq LLM]
        ├─ Send context + question
        ├─ Llama 3.3 70B processes
        └─ Generate answer
        ↓
[4. RESPONSE]
        ├─ Answer
        ├─ Sources
        └─ Metadata
        ↓
Student Receives Answer

---

## Testing

### **Test Groq Connection**

python test_groq_direct.py

### **Test Embeddings**

python test_embeddings.py

### **Manual API Testing**

Using FastAPI Swagger UI: `http://localhost:8000/docs`

Or using curl:
# Health check
curl http://localhost:8000/health

# Index PDFs
curl -X POST http://localhost:8000/api/index

# Query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is data structure?"}'

---

## Troubleshooting

### **Issue: "The model has been decommissioned"**

**Solution:** Update `.env` with a new model:
GROQ_MODEL=llama-3.3-70b-versatile

---

### **Issue: "GROQ_API_KEY not set"**

**Solution:** 
1. Check `.env` file exists
2. Verify Groq API key is set (not placeholder)
3. No extra spaces or quotes around key

---

### **Issue: "No PDFs found"**

**Solution:**
1. Check PDFs are in `assets/course_pdfs/`
2. Verify file extension is `.pdf` (lowercase)
3. Ensure PDFs aren't corrupted

---

### **Issue: "ChromaDB error: deprecated configuration"**

**Solution:** Already fixed in this version. If you see this, update `src/vector_store.py`.

---

### **Issue: "Connection refused" to localhost:8000**

**Solution:**
1. Ensure server is running: `python main.py`
2. Check port isn't in use: `netstat -ano | findstr :8000` (Windows)
3. Try different port in `.env`: `API_PORT=8001`

---

### **Issue: Slow responses from /api/query**

**Reasons & Solutions:**
- Large context: Reduce PDF size or use smaller model
- Network latency: Groq servers are responding (normal)
- First query: Groq model loads on first use (normal)

---

### **Issue: Query returns "An error occurred"**

**Solution:**
1. Check server terminal for detailed error
2. Verify Groq API key is valid
3. Check rate limits (Groq free tier has limits)
4. Run `test_groq_direct.py` to isolate issue

---

## Additional Resources

- **FastAPI Documentation** - https://fastapi.tiangolo.com/
- **LangChain Documentation** - https://python.langchain.com/
- **ChromaDB Documentation** - https://docs.trychroma.com/
- **Groq API Documentation** - https://console.groq.com/docs/
- **RAG Concepts** - https://aws.amazon.com/blogs/machine-learning/

---


## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

##  Author

**EduMate Development Team**

---

## Support

For issues, questions, or suggestions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review API Documentation
3. Check server terminal for error logs
4. Create an issue in the repository

---

## Educational Notes

This project demonstrates:
- ✅ RAG (Retrieval-Augmented Generation) architecture
- ✅ Vector databases and semantic search
- ✅ LLM integration and prompt engineering
- ✅ RESTful API design with FastAPI
- ✅ Production code structure and best practices
- ✅ Error handling and logging
- ✅ Environment variable management
- ✅ Git workflow and version control

---

## Next Steps

1. **Connect to Flutter App** - Use the API endpoints in your Flutter UI
2. **Add More Features** - User feedback, answer ratings, favorites
3. **Deploy to Production** - Host on cloud server (AWS, Azure, Heroku)
4. **Optimize Performance** - Add caching, database indexing
5. **Scale** - Handle multiple concurrent users

