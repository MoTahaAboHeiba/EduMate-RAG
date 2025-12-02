"""
Main entry point for EduMate RAG system
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    import uvicorn
    # Use string import path for reload to work
    uvicorn.run(
        "src.api.main:app",  # This is the import string format
        host="0.0.0.0",
        port=8010,
        reload=True
    )
