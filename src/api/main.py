"""
FastAPI server for EduMate RAG with conversation support
"""
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config import config
from src.document_processing.vector_store import vector_store
from src.core.rag_chain import rag_chain
from src.conversation.conversation_manager import conversation_manager

HEALTH_CACHE_TTL_SECONDS = 30
_health_cache = {
    "timestamp": 0.0,
    "collection_info": None,
}

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

@app.on_event("startup")
async def startup_event():
    collection_info = vector_store.get_collection_info()
    documents_indexed = collection_info["count"]

    if documents_indexed == 0:
        print("No indexed documents found. Starting PDF indexing...")
        vector_store.index_pdfs()
        print("PDF indexing complete.")
    else:
        print(f"Vector store already has {documents_indexed} indexed documents.")

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str
    num_context_docs: int = 3

class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: List[str]
    num_context_docs: int
    conversation_turn: int
    is_general: bool = False
    latency_ms: float = 0.0
    timings_ms: Dict[str, float] = {}

class IntegrationMessage(BaseModel):
    question: str
    answer: str

class IntegrationQueryRequest(BaseModel):
    user_id: str = Field(alias="userId")
    conversation_id: str = Field(alias="conversationId")
    message: str
    messages: List[IntegrationMessage] = Field(default_factory=list)
    num_context_docs: int = Field(default=3, alias="numContextDocs")

class IntegrationQueryResponse(BaseModel):
    user_id: str = Field(alias="userId")
    conversation_id: str = Field(alias="conversationId")
    question: str
    answer: str
    sources: List[str]
    num_context_docs: int = Field(alias="numContextDocs")
    is_general: bool = Field(default=False, alias="isGeneral")
    latency_ms: float = Field(default=0.0, alias="latencyMs")
    timings_ms: Dict[str, float] = Field(default_factory=dict, alias="timingsMs")

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
    start_time = time.perf_counter()
    now = time.time()

    if (
        _health_cache["collection_info"] is None
        or now - _health_cache["timestamp"] > HEALTH_CACHE_TTL_SECONDS
    ):
        _health_cache["collection_info"] = vector_store.get_collection_info()
        _health_cache["timestamp"] = now

    collection_info = _health_cache["collection_info"]
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "status": "healthy",
        "model": config.GROQ_MODEL,
        "latency_ms": latency_ms,
        "cache_ttl_seconds": HEALTH_CACHE_TTL_SECONDS,
        "vector_store": {
            "backend": config.VECTOR_STORE_BACKEND,
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
def query(
    request: QueryRequest,
    request_obj: Request,
    x_evaluation_mode: str = Header(None, alias="X-Evaluation-Mode"),
) -> QueryResponse:
    """Query the RAG system (with conversation memory)"""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if request.num_context_docs < 1 or request.num_context_docs > 10:
        raise HTTPException(status_code=400, detail="num_context_docs must be between 1 and 10")
    
    try:
        session_token = get_session_token(request_obj)
        persist_conversation = str(x_evaluation_mode).lower() not in {"1", "true", "yes"}
        start_time = time.perf_counter()
        try:
            result = rag_chain.query(
                request.question,
                session_token=session_token,
                num_context_docs=request.num_context_docs,
                persist_conversation=persist_conversation,
            )
        except RuntimeError as e:
            if "GROQ_RATE_LIMIT" in str(e):
                raise HTTPException(status_code=503, detail="Groq rate limit reached. Stop evaluation and try again later.")
            raise
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not result.get("answer", "").strip():
            raise RuntimeError("RAG chain returned an empty answer")

        
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            num_context_docs=result["num_context_docs"],
            conversation_turn=result["conversation_turn"],
            is_general=result.get("is_general", False),
            latency_ms=latency_ms,
            timings_ms=result.get("timings_ms", {}),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.post("/api/integrations/query", response_model=IntegrationQueryResponse)
def integration_query(request: IntegrationQueryRequest) -> IntegrationQueryResponse:
    """Stateless query endpoint for the .NET backend integration."""
    if not request.user_id.strip():
        raise HTTPException(status_code=400, detail="userId cannot be empty")

    if not request.conversation_id.strip():
        raise HTTPException(status_code=400, detail="conversationId cannot be empty")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    if request.num_context_docs < 1 or request.num_context_docs > 10:
        raise HTTPException(status_code=400, detail="numContextDocs must be between 1 and 10")

    try:
        bounded_history = request.messages[-5:]
        history = [item.model_dump() for item in bounded_history]
        start_time = time.perf_counter()
        try:
            result = rag_chain.query_with_history(
                question=request.message,
                history=history,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                num_context_docs=request.num_context_docs,
            )
        except RuntimeError as e:
            if "GROQ_RATE_LIMIT" in str(e):
                raise HTTPException(status_code=503, detail="Groq rate limit reached. Try again later.")
            raise
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if not result.get("answer", "").strip():
            raise RuntimeError("RAG chain returned an empty answer")

        return IntegrationQueryResponse(
            userId=request.user_id,
            conversationId=request.conversation_id,
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            numContextDocs=result["num_context_docs"],
            isGeneral=result.get("is_general", False),
            latencyMs=latency_ms,
            timingsMs=result.get("timings_ms", {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Integration API Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing integration query: {str(e)}")

@app.post("/api/index")
async def index(x_admin_key: str = Header(None, alias="X-Admin-Key")):
    """
    Re-index all PDFs in the database
    
    Returns:
        Success status and document count
    """
    # If ADMIN_KEY is not configured, disable this endpoint.
    if not config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin not configured")

    if x_admin_key != config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


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
    """Get the current conversation history"""
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
    """Clear the conversation memory (start fresh)"""
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
    """Get conversation statistics"""
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
    """Start a new conversation"""
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
    """List all saved conversations"""
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
    """Load a saved conversation"""
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
    """Delete a saved conversation"""
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
