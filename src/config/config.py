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

    # Runtime data should not live inside source-controlled assets.
    # Use /data on Hugging Face when persistent storage is mounted; otherwise
    # fall back to /tmp for ephemeral container storage.
    DEFAULT_RUNTIME_DIR = "/data/edumate" if Path("/data").exists() else "/tmp/edumate"
    
    # Groq Configuration
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    
    # ChromaDB Configuration
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(Path(DEFAULT_RUNTIME_DIR) / "chroma_db"))

    # Vector Store Configuration
    VECTOR_STORE_BACKEND = os.getenv("VECTOR_STORE_BACKEND", "qdrant").lower()
    QDRANT_URL = os.getenv("QDRANT_URL")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    
    # PDF Configuration
    PDF_FOLDER_PATH = os.getenv("PDF_FOLDER_PATH", "./assets/course_pdfs")
    
    # Conversation Configuration
    CONVERSATION_DIR = os.getenv("CONVERSATION_DIR", str(Path(DEFAULT_RUNTIME_DIR) / "conversations"))
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = int(os.getenv("API_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    ADMIN_KEY = os.getenv("ADMIN_KEY")

    def _ensure_directory(self, path_value: str, setting_name: str) -> None:
        path = Path(path_value)
        if path.exists() and not path.is_dir():
            raise ValueError(f"{setting_name} points to a file, not a directory: {path}")
        path.mkdir(parents=True, exist_ok=True)
    
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
            self._ensure_directory(self.CHROMA_DB_PATH, "CHROMA_DB_PATH")
        self._ensure_directory(self.PDF_FOLDER_PATH, "PDF_FOLDER_PATH")
        self._ensure_directory(self.CONVERSATION_DIR, "CONVERSATION_DIR")

# Create global config instance
config = Config()
