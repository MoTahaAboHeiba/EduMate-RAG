"""
FastAPI server for EduMate RAG
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import config
from src.vector_store import vector_store
from src.rag_chain import rag_chain

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

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list
    num_context_docs: int

# Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EduMate RAG API is running!",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    collection_info = vector_store.get_collection_info()
    return {
        "status": "healthy",
        "model": config.GROQ_MODEL,
        "vector_store": {
            "collection": collection_info["collection_name"],
            "documents_indexed": collection_info["count"]
        }
    }

@app.post("/api/query")
async def query(request: QueryRequest) -> QueryResponse:
    """
    Query the RAG system
    
    Args:
        request: QueryRequest with question field
    
    Returns:
        QueryResponse with answer and sources
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Query RAG chain
        result = rag_chain.query(request.question)
        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            num_context_docs=result["num_context_docs"]
        )
    
    except Exception as e:
        print(f"❌ API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/api/index")
async def index():
    """
    Re-index all PDFs in the database
    """
    try:
        success = vector_store.index_pdfs()
        
        if success:
            collection_info = vector_store.get_collection_info()
            return {
                "status": "success",
                "message": "PDFs indexed successfully",
                "documents_indexed": collection_info["count"]
            }
        else:
            raise HTTPException(status_code=400, detail="Indexing failed")
    
    except Exception as e:
        print(f"❌ Indexing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing PDFs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT
    )
