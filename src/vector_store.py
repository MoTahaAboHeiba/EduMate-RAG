"""
Vector store backends for EduMate RAG.
"""
from pathlib import Path
import time
from typing import List
from uuid import uuid5, NAMESPACE_URL

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from src.config import config
from src.pdf_loader import pdf_loader


COLLECTION_NAME = "course_materials"


class ChromaVectorStore:
    """Local ChromaDB vector store for development."""

    def __init__(self):
        Path(config.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=config.CHROMA_DB_PATH)
        self.collection_name = COLLECTION_NAME
        self.embedding_function = DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def index_pdfs(self):
        print("Starting PDF indexing...")

        documents = pdf_loader.load_all_pdfs()

        if not documents:
            print("No documents to index")
            return False

        print(f"Adding {len(documents)} documents to ChromaDB...")

        batch_size = 64
        for start in range(0, len(documents), batch_size):
            batch = documents[start:start + batch_size]
            try:
                texts = [doc["content"] for doc in batch]
                self.collection.add(
                    ids=[self._document_id(doc, start + offset) for offset, doc in enumerate(batch)],
                    documents=texts,
                    embeddings=self._embed_texts(texts),
                    metadatas=[doc["metadata"] for doc in batch],
                )

                indexed = min(start + batch_size, len(documents))
                print(f"  Indexed {indexed}/{len(documents)} documents")
                
            except Exception as e:
                print(f"   Error indexing batch starting at {start}: {e}")

        print(f" Indexing complete! Total documents: {len(documents)}")
        return True

    def similarity_search(self, query: str, k: int = 3) -> List[dict]:
        try:
            results = self.collection.query(
                query_embeddings=[self._embed_texts([query])[0]],
                n_results=k,
            )

            documents = []
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })

            return documents

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def search(self, query: str, num_results: int = 3) -> List[dict]:
        return self.similarity_search(query, k=num_results)

    def get_collection_info(self) -> dict:
        return {
            "collection_name": self.collection_name,
            "count": self.collection.count(),
        }

    def _document_id(self, doc: dict, idx: int) -> str:
        metadata = doc["metadata"]
        return f"{metadata['source']}_{metadata['chunk_index']}_{idx}"

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.embedding_function(texts)
        return [[float(value) for value in embedding] for embedding in embeddings]


class QdrantVectorStore:
    """Qdrant Cloud vector store for production."""

    def __init__(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
        except ImportError as exc:
            raise ImportError(
                "qdrant-client is required when VECTOR_STORE_BACKEND=qdrant"
            ) from exc

        self.client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY,
            timeout=120,
        )
        self.collection_name = COLLECTION_NAME
        self.embedding_function = DefaultEmbeddingFunction()
        self.vector_size = len(self._embed_texts(["dimension probe"])[0])

        if not self._collection_exists():
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def index_pdfs(self):
        try:
            from qdrant_client.models import PointStruct
        except ImportError as exc:
            raise ImportError(
                "qdrant-client is required when VECTOR_STORE_BACKEND=qdrant"
            ) from exc

        print("Starting PDF indexing...")

        documents = pdf_loader.load_all_pdfs()

        if not documents:
            print("No documents to index")
            return False

        print(f"Adding {len(documents)} documents to Qdrant...")

        batch_size = 32
        failed_batches = []
        for start in range(0, len(documents), batch_size):
            batch = documents[start:start + batch_size]
            vectors = self._embed_texts([doc["content"] for doc in batch])
            points = []

            for offset, doc in enumerate(batch):
                idx = start + offset
                point_id = self._point_id(doc, idx)
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vectors[offset],
                        payload={
                            "content": doc["content"],
                            "metadata": doc["metadata"],
                        },
                    )
                )

            if self._upsert_with_retry(points, start):
                print(f"  Indexed {min(start + batch_size, len(documents))}/{len(documents)} documents")
            else:
                failed_batches.append(start)

        if failed_batches:
            print(f" Indexing incomplete. Failed batch starts: {failed_batches}")
            return False

        print(f" Indexing complete! Total documents: {len(documents)}")
        return True

    def similarity_search(self, query: str, k: int = 3) -> List[dict]:
        try:
            query_vector = self._embed_texts([query])[0]
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=k,
                with_payload=True,
            )

            documents = []
            for result in results:
                payload = result.payload or {}
                documents.append({
                    "content": payload.get("content", ""),
                    "metadata": payload.get("metadata", {}),
                    "distance": result.score,
                })

            return documents

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def search(self, query: str, num_results: int = 3) -> List[dict]:
        return self.similarity_search(query, k=num_results)

    def get_collection_info(self) -> dict:
        count = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        ).count

        return {
            "collection_name": self.collection_name,
            "count": count,
        }

    def _collection_exists(self) -> bool:
        try:
            self.client.get_collection(collection_name=self.collection_name)
            return True
        except Exception:
            return False

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.embedding_function(texts)
        return [[float(value) for value in embedding] for embedding in embeddings]

    def _point_id(self, doc: dict, idx: int) -> str:
        metadata = doc["metadata"]
        raw_id = f"{self.collection_name}:{metadata['source']}:{metadata['chunk_index']}:{idx}"
        return str(uuid5(NAMESPACE_URL, raw_id))

    def _upsert_with_retry(self, points, start: int, attempts: int = 3) -> bool:
        for attempt in range(1, attempts + 1):
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=False,
                )
                return True
            except Exception as e:
                print(f"   Error indexing batch starting at {start} (attempt {attempt}/{attempts}): {e}")
                if attempt < attempts:
                    time.sleep(2 * attempt)

        return False


class VectorStore:
    """Backend-neutral vector store facade."""

    def __init__(self):
        if config.VECTOR_STORE_BACKEND == "qdrant":
            self.backend = QdrantVectorStore()
        else:
            self.backend = ChromaVectorStore()

    def index_pdfs(self):
        return self.backend.index_pdfs()

    def similarity_search(self, query: str, k: int = 3) -> List[dict]:
        return self.backend.similarity_search(query, k=k)

    def search(self, query: str, num_results: int = 3) -> List[dict]:
        return self.backend.search(query, num_results=num_results)

    def get_collection_info(self) -> dict:
        return self.backend.get_collection_info()

    def __getattr__(self, name):
        return getattr(self.backend, name)


vector_store = VectorStore()
