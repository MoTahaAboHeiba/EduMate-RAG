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
    
    # PDF Configuration
    PDF_FOLDER_PATH = os.getenv("PDF_FOLDER_PATH", "./assets/course_pdfs")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "localhost")
    API_PORT = int(os.getenv("API_PORT", 8000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    def __init__(self):
        """Validate configuration"""
        if not self.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set in .env file")
        
        # Create directories if they don't exist
        Path(self.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
        Path(self.PDF_FOLDER_PATH).mkdir(parents=True, exist_ok=True)

# Create global config instance
config = Config()
