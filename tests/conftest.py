import sys
from unittest.mock import MagicMock

# Define dummy environment variables for testing before config loads
import os
os.environ["GROQ_API_KEY"] = "mock_groq_key"
os.environ["ADMIN_KEY"] = "mock_admin_key"
os.environ["VECTOR_STORE_BACKEND"] = "chroma"

# Mock the database clients to prevent network/file I/O during imports and collection
sys.modules['chromadb'] = MagicMock()
sys.modules['chromadb.utils'] = MagicMock()
sys.modules['chromadb.utils.embedding_functions'] = MagicMock()
sys.modules['qdrant_client'] = MagicMock()
sys.modules['qdrant_client.models'] = MagicMock()
sys.modules['qdrant_client.models.models'] = MagicMock()
