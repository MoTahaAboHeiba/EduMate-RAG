"""
Hugging Face Spaces entry point for EduMate RAG.

The Dockerfile starts `src.api.main:app` directly, but keeping this module at
the repo root makes the Space layout explicit and lets Python-SDK launches use
`python app.py` if needed.
"""
import os

import uvicorn

from src.api.main import app


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        workers=1,
    )
