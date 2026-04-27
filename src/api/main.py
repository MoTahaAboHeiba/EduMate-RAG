"""
FastAPI server for EduMate RAG with conversation support
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sys
from pathlib import Path
from typing import List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import config
from src.vector_store import vector_store
from src.rag_chain import rag_chain
from src.conversation_manager import conversation_manager

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
    is_general: bool = False

class ConversationMessage(BaseModel):
    role: str  # "student" or "assistant"
    content: str

class ConversationHistoryResponse(BaseModel):
    total_turns: int
    messages: List[ConversationMessage]

# Endpoints

def get_session_token(request: Request) -> str:
    token = request.headers.get("X-Session-Token")
    return token if token else "anonymous"

@app.get("/")
async def root():
    """Root endpoint - serves the UI"""
    static_path = Path(__file__).parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path)
    return {
        "message": "EduMate RAG API is running!",
        "version": "2.0.0",
        "features": ["PDF Q&A", "Conversation Memory", "Source Attribution"]
    }

@app.get("/api")
async def api_root():
    """API root endpoint"""
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
async def query(request: QueryRequest, request_obj: Request) -> QueryResponse:
    """
    Query the RAG system (with conversation memory)
    
    Args:
        request: QueryRequest with question field
        request_obj: FastAPI Request for session token extraction
    
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
        session_token = get_session_token(request_obj)
        result = rag_chain.query(request.question, session_token=session_token)
        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            num_context_docs=result["num_context_docs"],
            conversation_turn=result["conversation_turn"],
            is_general=result.get("is_general", False)
        )
    
    except Exception as e:
        print(f"API Error: {e}")
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
        print(f"Indexing Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error indexing PDFs: {str(e)}")

@app.get("/api/conversation/history")
async def get_conversation_history(request_obj: Request) -> ConversationHistoryResponse:
    """
    Get the current conversation history
    
    Returns:
        List of all messages in current conversation
    
    Example:
        GET /api/conversation/history
    """
    try:
        session_token = get_session_token(request_obj)
        history = rag_chain.get_conversation_history(session_token=session_token)
        summary = rag_chain.get_memory_summary(session_token=session_token)
        
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
async def clear_conversation(request_obj: Request):
    """
    Clear the conversation memory (start fresh)
    
    Returns:
        Success message
    
    Example:
        POST /api/conversation/clear
    """
    try:
        session_token = get_session_token(request_obj)
        rag_chain.clear_memory(session_token=session_token)
        return {
            "status": "success",
            "message": "Conversation memory cleared",
            "note": "Next question will start a new conversation"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing memory: {str(e)}")

@app.get("/api/conversation/info")
async def get_conversation_info(request_obj: Request):
    """
    Get conversation statistics
    
    Returns:
        Information about current conversation
    
    Example:
        GET /api/conversation/info
    """
    try:
        session_token = get_session_token(request_obj)
        summary = rag_chain.get_memory_summary(session_token=session_token)
        conv_id = rag_chain.get_current_conversation_id(session_token=session_token)
        return {
            "total_turns": summary["total_turns"],
            "total_messages": summary["total_messages"],
            "status": "active" if summary["total_messages"] > 0 else "empty",
            "conversation_id": conv_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting info: {str(e)}")

@app.post("/api/conversation/new")
async def start_new_conversation(request_obj: Request, title: str = ""):
    """
    Start a new conversation (save current one if exists)
    
    Args:
        request_obj: FastAPI Request for session token extraction
        title: Optional title for the conversation
    
    Returns:
        New conversation ID
    
    Example:
        POST /api/conversation/new?title=Advanced%20Math
    """
    try:
        session_token = get_session_token(request_obj)
        conv_id = rag_chain.start_new_conversation(session_token=session_token, title=title or None)
        return {
            "status": "success",
            "conversation_id": conv_id,
            "message": "New conversation started"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@app.get("/api/conversation/list")
async def list_conversations(request_obj: Request, limit: int = 10):
    """
    List all saved conversations
    
    Args:
        limit: Maximum number to return (default 10)
    
    Returns:
        List of conversation summaries
    
    Example:
        GET /api/conversation/list?limit=20
    """
    try:
        session_token = get_session_token(request_obj)
        conversations = rag_chain.list_saved_conversations(limit=limit, session_token=session_token)
        return {
            "status": "success",
            "count": len(conversations),
            "conversations": conversations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")

@app.post("/api/conversation/load/{conversation_id}")
async def load_conversation(conversation_id: str, request_obj: Request):
    """
    Load a saved conversation
    
    Args:
        conversation_id: ID of conversation to load
        request_obj: FastAPI Request for session token extraction
    
    Returns:
        Loaded conversation data
    
    Example:
        POST /api/conversation/load/conv_20260216_153045
    """
    try:
        session_token = get_session_token(request_obj)
        success = rag_chain.load_conversation(conversation_id, session_token=session_token)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the loaded conversation data to return messages
        conv_data = conversation_manager.get_conversation(conversation_id, session_token=session_token)
        
        return {
            "status": "success",
            "conversation_id": conversation_id,
            "message": "Conversation loaded",
            "conversation": conv_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading conversation: {str(e)}")

@app.delete("/api/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str, request_obj: Request):
    """
    Delete a saved conversation
    
    Args:
        conversation_id: ID of conversation to delete
        request_obj: FastAPI Request for session token extraction
    
    Returns:
        Success status
    
    Example:
        DELETE /api/conversation/conv_20260216_153045
    """
    try:
        session_token = get_session_token(request_obj)
        success = rag_chain.delete_conversation(conversation_id, session_token=session_token)
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "status": "success",
            "message": "Conversation deleted",
            "conversation_id": conversation_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting conversation: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.API_HOST,
        port=config.API_PORT
    )
