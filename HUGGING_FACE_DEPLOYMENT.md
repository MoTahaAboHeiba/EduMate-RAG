# 🤗 Hugging Face Production Deployment Guide

**Deploy EduMate RAG to Hugging Face Spaces with full production support**

---

## Table of Contents
1. [Overview](#overview)
2. [Deployment Options](#deployment-options)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [Configuration](#configuration)
6. [Monitoring](#monitoring)
7. [Cost Analysis](#cost-analysis)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Why Hugging Face?

✅ **Free Tier Available** - Run Spaces for free with limitations
✅ **GPU Support** - Optional GPU acceleration
✅ **Easy Deployment** - Git push to deploy
✅ **Community** - Share & showcase your project
✅ **Built-in Tools** - Models, Datasets, Spaces hub

### What You Get

```
Before: Your laptop
└─ Limited concurrent users
└─ No persistent storage
└─ Manual restarts

After: Hugging Face
├─ 100+ concurrent users
├─ Auto-scaling
├─ Persistent vector DB (Qdrant Cloud)
├─ Health checks & monitoring
└─ Custom domain (optional)
```

---

## Deployment Options

### Option A: Spaces (Recommended for MVP)

**Pros:**
- Free to start
- Auto-restarts on inactivity
- Can add GPU
- Easy to manage
- Good for demos

**Cons:**
- Shuts down after 48h inactivity
- Limited RAM (16GB)
- Limited concurrency

**Cost:** Free → $7/month with GPU

**Best For:** Testing, demos, medium load

### Option B: Inference Endpoints (Production Grade)

**Pros:**
- Always running
- Auto-scales
- SLA guarantee
- Private endpoints
- Higher concurrency

**Cons:**
- Paid only
- Need custom wrapper

**Cost:** $0.06/hour per replica (~$45/month)

**Best For:** Production, high concurrency

### Option C: Models Hub (Data Storage Only)

**Pros:**
- Free forever
- Version control
- Good for large models
- Community integration

**Cons:**
- No compute
- Manual updates

**Cost:** Free

**Best For:** Storing model versions

---

## Prerequisites

### Accounts & Setup
- [ ] Hugging Face account (free at huggingface.co)
- [ ] Qdrant Cloud account (vector DB persistence)
- [ ] GitHub repository with code pushed
- [ ] Groq API key ready
- [ ] Docker basics understanding

### Local Setup
```bash
# Install Hugging Face CLI
pip install huggingface-hub

# Login
huggingface-cli login
# Paste your HF token from https://huggingface.co/settings/tokens
```

---

## Step-by-Step Guide

### Step 1: Create Hugging Face Space

1. Go to https://huggingface.co/new-space
2. **Space name:** `edumate-rag` (or your preference)
3. **License:** `mit` or your choice
4. **Space SDK:** Select **Docker**
5. **Visibility:** Public or Private
6. **Create Space**

You'll get a GitHub-like repository ready for code.

### Step 2: Prepare Your Repository

Clone the HF Space to your machine:

```bash
# Clone the space repo
git clone https://huggingface.co/spaces/yourusername/edumate-rag
cd edumate-rag

# Copy your EduMate code here
cp -r ../EduMate-RAG/* .

# You should have:
# ├── src/
# ├── tests/
# ├── requirements.txt
# ├── Dockerfile
# ├── README.md
# └── app.py (create this - see next step)
```

### Step 3: Create app.py (Entry Point)

Create `app.py` in the root directory:

```python
#!/usr/bin/env python3
"""
EduMate RAG - Hugging Face Spaces Wrapper

Provides FastAPI endpoints accessible from HF Spaces.
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import EduMate modules
from api.main import app as edumate_app

# Get port from environment (HF sets PORT variable)
PORT = int(os.getenv("PORT", 7860))
HOST = "0.0.0.0"

# Health check endpoint
@edumate_app.get("/health")
async def health():
    """Health check for HF monitoring"""
    return {
        "status": "healthy",
        "service": "EduMate RAG",
        "version": "1.0.0"
    }

# CORS middleware for Flutter app
edumate_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    
    print(f"🚀 Starting EduMate RAG on {HOST}:{PORT}")
    print(f"📚 API Documentation: http://{HOST}:{PORT}/docs")
    print(f"🔥 Health Check: http://{HOST}:{PORT}/health")
    
    uvicorn.run(
        edumate_app,
        host=HOST,
        port=PORT,
        workers=1  # Important: Single worker for conversation memory
    )
```

### Step 4: Create Dockerfile for HF

Create `Dockerfile` in root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY app.py .
COPY .env.example .env

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:7860/health')"

# Run app
CMD ["python", "app.py"]
```

### Step 5: Create .huggingface/README.md

Create `.huggingface/README.md` with space metadata:

```markdown
---
title: EduMate RAG
emoji: 📚
colorFrom: blue
colorTo: green
sdk: docker
sdk_version: latest
app_file: app.py
pinned: false
---

# EduMate RAG - Intelligent Course Q&A

Production-ready RAG system for university course questions.

## Features
- 📚 PDF-based Q&A
- ⚡ Sub-second search
- 🔄 Multi-turn conversations
- 🌍 Multilingual support

## Usage

```bash
curl -X POST https://your-space-url/api/query \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: user123" \
  -d '{"question": "What is photosynthesis?"}'
```

## Documentation

See [MASTER_PRESENTATION.md](../MASTER_PRESENTATION.md) for complete guide.
```

### Step 6: Configure Environment Variables

1. Go to your Space Settings → Secrets
2. Add these secrets:

```
GROQ_API_KEY=your_actual_key_from_console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile

VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=your_qdrant_cloud_url
QDRANT_API_KEY=your_qdrant_api_key

PDF_FOLDER_PATH=/app/assets/course_pdfs
CHROMA_DB_PATH=/app/assets/chroma_db

DEBUG=False
API_HOST=0.0.0.0
API_PORT=7860
```

### Step 7: Update requirements.txt

Ensure all dependencies are specified:

```
fastapi==0.109.2
uvicorn==0.27.0
python-dotenv==1.0.1
langchain==0.1.20
langchain-community==0.0.38
langchain-groq==0.0.15
chromadb==0.4.22
qdrant-client==1.9.1
pypdf==4.0.1
PyMuPDF==1.24.9
pydantic==2.5.3
pydantic-settings==2.1.0
requests==2.31.0
psutil==5.9.6
```

### Step 8: Push to Hugging Face

```bash
git add .
git commit -m "Deploy EduMate to HF Spaces"
git push
```

HF will automatically:
1. Build Docker image
2. Start container
3. Run health checks
4. Make endpoint live

**Wait 2-5 minutes for deployment.**

### Step 9: Access Your Deployment

Your Space URL: `https://huggingface.co/spaces/yourusername/edumate-rag`

API Access: `https://yourusername-edumate-rag.hf.space`

Test it:

```bash
curl https://yourusername-edumate-rag.hf.space/health
```

---

## Configuration

### startup Behavior

Your app will:

1. Load `.env` variables from HF Secrets
2. Initialize vector DB (Qdrant)
3. Auto-index PDFs on first startup
4. Start FastAPI server
5. Accept requests

### Persistent Storage

HF Spaces **restart after 48 hours of inactivity**. To keep data:

**Use Qdrant Cloud:**
```env
VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your_key
```

Vectors persist in Qdrant Cloud (not lost on restart).

### Custom Domain (Optional)

To use your own domain:

1. Go to Space Settings → Models & Datasets
2. Set custom domain: `edumate.yourdomain.com`
3. Update DNS CNAME to HF

---

## Monitoring

### Health Checks

```bash
# Every 30 seconds, HF checks:
curl https://yourusername-edumate-rag.hf.space/health

# Should return:
{"status": "healthy", "documents_indexed": 5637}
```

If health check fails 3 times, HF restarts the container.

### Logs

View logs in:
1. Space Settings → Logs
2. Shows startup output and errors
3. Useful for debugging

### Metrics

Track in your own monitoring:

```python
# In your app, expose metrics endpoint
@app.get("/metrics")
def metrics():
    return {
        "uptime_seconds": get_uptime(),
        "requests_total": request_count,
        "avg_latency_ms": avg_latency,
        "vectors_indexed": vector_count
    }
```

---

## Cost Analysis

### Option A: HF Spaces (Free)

| Component | Cost | Notes |
|-----------|------|-------|
| Compute | Free | Pauses after 48h inactivity |
| Storage | Free | 10GB limit |
| Bandwidth | Free | Included |
| Vector DB (Qdrant Cloud) | $8-25/month | Persistent vectors |
| **Total** | **~$8-25/month** | Good for MVP |

### Option B: HF Spaces + GPU

| Component | Cost | Notes |
|-----------|------|-------|
| Compute (T4 GPU) | $7/month | Always running |
| Storage | Free | 10GB limit |
| Bandwidth | Free | Included |
| Vector DB | $8-25/month | Persistent |
| **Total** | **~$15-32/month** | Faster inference |

### Option C: HF Inference Endpoints

| Component | Cost | Notes |
|-----------|------|-------|
| Compute (CPU) | $0.06/hour | ~$45/month for 1 replica |
| Auto-scaling | +$0.06/hour per replica | Scale to 2-5 replicas |
| Storage | Included | 5GB minimum |
| **Total** | **$45-250+/month** | Production scale |

### Cost Recommendation

- **MVP/Testing:** Free HF Spaces + Qdrant Cloud (Free tier)
- **Low Traffic:** Free HF Spaces + Qdrant Cloud (Paid)
- **Production:** HF Inference Endpoints or Railway

---

## Troubleshooting

### 1. Container Won't Start

**Check logs:**
```
Settings → Logs → View startup output
```

**Common issues:**
- Missing requirements
- Bad Python version
- Syntax error in app.py

**Solution:**
```bash
# Test locally
docker build -t edumate .
docker run -p 7860:7860 edumate
```

### 2. Health Checks Failing

**Error:** Container keeps restarting

**Causes:**
- GROQ_API_KEY invalid
- QDRANT_URL unreachable
- Memory limit exceeded

**Solution:**
1. Check secrets in Settings
2. Verify Qdrant URL works
3. Reduce PDF_CHUNK_SIZE to save memory

### 3. Vector DB Not Indexing

**Error:** `"documents_indexed": 0`

**Causes:**
- PDFs not found
- QDRANT_API_KEY invalid
- PDF format unsupported

**Solution:**
```bash
# In Space logs, check indexing:
"Found 5 PDF(s)"
"Total chunks created: 5637"
```

If zero chunks:
- Try PyMuPDF fallback
- Check PDF format
- Split large PDFs

### 4. Slow Responses

**Latency >200ms from HF Space**

**Causes:**
- Qdrant Cloud network latency
- Too many concurrent requests
- Vector DB overloaded

**Solution:**
1. Use Qdrant Local instead of Cloud
2. Reduce RETRIEVAL_TOP_K
3. Add caching layer
4. Scale to multiple replicas

### 5. Out of Memory

**Error:** Process killed (OOM)

**Causes:**
- Too many vectors
- Large batch indexing
- Memory leak

**Solution:**
1. Reduce PDF_CHUNK_SIZE
2. Index PDFs in smaller batches
3. Use Qdrant Cloud (offload vectors)

---

## Advanced Customization

### Custom UI (Optional Gradio)

If you want a web interface:

```python
import gradio as gr
from app import query_edumate

def chatbot_ui(question, session_token="default"):
    answer = query_edumate(question, session_token)
    return answer

interface = gr.Interface(
    fn=chatbot_ui,
    inputs=["text", "text"],
    outputs="text",
    title="EduMate RAG"
)

interface.launch(share=True)
```

### Private Space

To restrict access:

1. Space Settings → Visibility → Private
2. Add collaborators
3. Only invited users can access

### Scheduled Indexing

To re-index PDFs periodically:

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('interval', hours=24)
def scheduled_indexing():
    """Re-index PDFs every 24 hours"""
    pdf_loader.index_pdfs()
    logger.info("Daily indexing complete")

scheduler.start()
```

---

## Production Checklist

- [ ] Space created on Hugging Face
- [ ] Docker image builds locally
- [ ] All secrets configured
- [ ] Health checks passing
- [ ] PDFs indexed successfully
- [ ] Queries working end-to-end
- [ ] Logs being monitored
- [ ] Custom domain configured (optional)
- [ ] README updated with usage
- [ ] Rate limiting configured
- [ ] Error handling tested
- [ ] Performance acceptable
- [ ] Backup strategy in place
- [ ] Documentation complete

---

## Next Steps

1. **Create Space** on huggingface.co
2. **Set up locally** - test Docker build
3. **Configure secrets** - add API keys
4. **Push code** - git push to HF
5. **Monitor** - watch logs during startup
6. **Test** - make a query via API
7. **Share** - send Space URL to others

---

## Support Resources

- **Hugging Face Docs:** https://huggingface.co/docs/hub/spaces
- **Docker Guide:** https://docs.docker.com
- **EduMate Issues:** https://github.com/MoTahaAboHeiba/EduMate-RAG/issues
- **Community:** Hugging Face community tab

---

**Ready to go production?** Push to Hugging Face Spaces now! 🚀
