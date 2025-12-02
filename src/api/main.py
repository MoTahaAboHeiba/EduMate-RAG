"""
FastAPI server for EduMate RAG
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import config

# Create FastAPI app
app = FastAPI(
    title="EduMate RAG API",
    description="API for EduMate Retrieval-Augmented Generation system",
    version="1.0.0"
)

# Add CORS middleware (for Flutter app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "EduMate RAG API is running!"}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "model": config.GROQ_MODEL}

@app.post("/api/query")
async def query(question: str):
    """Query the RAG system"""
    return {"question": question, "answer": "RAG system coming soon..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT
    )
