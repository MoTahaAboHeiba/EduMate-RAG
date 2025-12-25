"""
FastAPI server for EduMate RAG with conversation support
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import config
from src.vector_store import vector_store
from src.rag_chain import rag_chain

# Create FastAPI app
app = FastAPI(
    title="EduMate RAG API",
    description="API for EduMate Retrieval-Augmented Generation system with conversation support",
    version="2.0.0"
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
    sources: List[str]
    num_context_docs: int
    conversation_turn: int

class ConversationMessage(BaseModel):
    role: str  # "student" or "assistant"
    content: str

class ConversationHistoryResponse(BaseModel):
    total_turns: int
    messages: List[ConversationMessage]

# Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "EduMate RAG API is running!",
        "version": "2.0.0",
        "features": ["PDF Q&A", "Conversation Memory", "Source Attribution"]
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
        },
        "features": {
            "conversation_memory": True,
            "multi_turn_support": True,
            "context_awareness": True
        }
    }

@app.post("/api/query")
async def query(request: QueryRequest) -> QueryResponse:
    """
    Query the RAG system (with conversation memory)
    
    Args:
        request: QueryRequest with question field
    
    Returns:
        QueryResponse with answer, sources, and conversation turn
    
    Example:
        POST /api/query
        {
            "question": "What are the prerequisites?"
        }
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Query RAG chain (with conversation memory)
        result = rag_chain.query(request.question)
        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            num_context_docs=result["num_context_docs"],
            conversation_turn=result["conversation_turn"]
        )
    
    except Exception as e:
        print(f" API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/api/index")
async def index():
    """
    Re-index all PDFs in the database
    
    Returns:
        Success status and document count
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
        print(f" indexing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing PDFs: {str(e)}")

@app.get("/api/conversation/history")
async def get_conversation_history() -> ConversationHistoryResponse:
    """
    Get the current conversation history
    
    Returns:
        List of all messages in current conversation
    
    Example:
        GET /api/conversation/history
    """
    try:
        history = rag_chain.get_conversation_history()
        summary = rag_chain.get_memory_summary()
        
        return ConversationHistoryResponse(
            total_turns=summary["total_turns"],
            messages=[
                ConversationMessage(role=msg["role"], content=msg["content"])
                for msg in history
            ]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")

@app.post("/api/conversation/clear")
async def clear_conversation():
    """
    Clear the conversation memory (start fresh)
    
    Returns:
        Success message
    
    Example:
        POST /api/conversation/clear
    """
    try:
        rag_chain.clear_memory()
        return {
            "status": "success",
            "message": "Conversation memory cleared",
            "note": "Next question will start a new conversation"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/api/conversation/info")
async def get_conversation_info():
    """
    Get conversation statistics
    
    Returns:
        Information about current conversation
    
    Example:
        GET /api/conversation/info
    """
    try:
        summary = rag_chain.get_memory_summary()
        return {
            "total_turns": summary["total_turns"],
            "total_messages": summary["total_messages"],
            "status": "active" if summary["total_messages"] > 0 else "empty"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT
    )
