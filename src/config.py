"""
Configuration management for EduMate RAG
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    """Application configuration"""
    
    # Groq Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./assets/chroma_db")

    # Vector Store Configuration
    VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE_BACKEND", "qdrant").lower()
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    
    # PDF Configuration
    PDF_FOLDER_PATH = os.getenv("PDF_FOLDER_PATH", "./assets/course_pdfs")
    
    # Conversation Configuration
    CONVERSATION_DIR = os.getenv("CONVERSATION_DIR", "./assets/conversations")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = int(os.getenv("API_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ADMIN_KEY = os.getenv("ADMIN_KEY")
    
    # LLM Optimization Configuration (Phase 5 & 6)
    # Temperature: Lower = more deterministic, less hallucination (0.3-0.5 recommended)
    # Phase 6: Default 0.3 for more grounded responses (was 0.5 in Phase 5)
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", 0.3))
    # Max tokens: Higher = more complete answers (1500-2000 recommended)
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", 1500))
    
    # Phase 6: Stricter validation settings
    # Grounding threshold: % of answer that must be in context (higher = stricter)
    GROUNDING_THRESHOLD = float(os.getenv("GROUNDING_THRESHOLD", 0.6))
    # Enforce validation: If True, reject answers below threshold
    ENFORCE_VALIDATION = os.getenv("ENFORCE_VALIDATION", "true").lower() == "true"
    
    # Retrieval Optimization Configuration (Phase 5)
    # Chunk size: Smaller chunks = better precision, larger = more context
    PDF_CHUNK_SIZE = int(os.getenv("PDF_CHUNK_SIZE", 800))  # Default 800, test: 512, 1024, 2048
    PDF_CHUNK_OVERLAP = int(os.getenv("PDF_CHUNK_OVERLAP", 200))
    # Number of documents to retrieve: Increase for better recall
    RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 5))  # Retrieve 5 docs, filter top-3
    # Similarity threshold: Higher = more strict retrieval
    RETRIEVAL_SIMILARITY_THRESHOLD = float(os.getenv("RETRIEVAL_SIMILARITY_THRESHOLD", 0.0))  # 0.0 = no filtering
    
    # Validation Configuration (Phase 5 & 6)
    # Enable retrieval validation: Check if answer is grounded in context
    ENABLE_RETRIEVAL_VALIDATION = os.getenv("ENABLE_RETRIEVAL_VALIDATION", "true").lower() == "true"
    # Enable reranking: Use cross-encoder to rerank results
    ENABLE_RERANKING = os.getenv("ENABLE_RERANKING", "false").lower() == "true"
    
    # Phase 6: Advanced retrieval tuning
    # Enable strict similarity filtering
    ENABLE_SIMILARITY_FILTERING = os.getenv("ENABLE_SIMILARITY_FILTERING", "false").lower() == "true"
    # Similarity threshold for filtering (0.3-0.7 recommended)
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.3))
    
    def __init__(self):
        """Validate configuration"""
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")

        if not self.ADMIN_KEY:
            raise ValueError("ADMIN_KEY not set")

        if self.VECTOR_STORE_BACKEND not in {"chroma", "qdrant"}:
            raise ValueError("VECTOR_STORE_BACKEND must be either 'chroma' or 'qdrant'")

        if self.VECTOR_STORE_BACKEND == "qdrant":
            if not self.QDRANT_URL:
                raise ValueError("QDRANT_URL must be set when VECTOR_STORE_BACKEND=qdrant")
            if not self.QDRANT_API_KEY:
                raise ValueError("QDRANT_API_KEY must be set when VECTOR_STORE_BACKEND=qdrant")
            if "your" in self.QDRANT_URL.lower():
                raise ValueError("QDRANT_URL contains a placeholder value. Set your real Qdrant Cloud URL.")
            if "your" in self.QDRANT_API_KEY.lower():
                raise ValueError("QDRANT_API_KEY contains a placeholder value. Set your real Qdrant API key.")
        
        # Create directories if they don't exist
        if self.VECTOR_STORE_BACKEND == "chroma":
            Path(self.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.PDF_FOLDER_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.CONVERSATION_DIR).mkdir(parents=True, exist_ok=True)

# Create global config instance
config = Config()
