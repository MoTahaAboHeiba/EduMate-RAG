"""
Vector Store - ChromaDB integration for RAG
"""
from typing import List
import chromadb
from pathlib import Path
from src.config import config
from src.pdf_loader import pdf_loader

class VectorStore:
    """Manage ChromaDB vector database"""
    
    def __init__(self):
        """Initialize ChromaDB client"""
        # Create persist directory if it doesn't exist
        Path(config.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
        
        # New ChromaDB client (using PersistentClient)
        self.client = chromadb.PersistentClient(
            path=config.CHROMA_DB_PATH
        )
        
        self.collection_name = "course_materials"
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def index_pdfs(self):
        """
        Load PDFs and create vector embeddings
        """
        print("Starting PDF indexing...")
        
        # Load all PDFs
        documents = pdf_loader.load_all_pdfs()
        
        if not documents:
            print(" No documents to index")
            return False
        
        # Add documents to ChromaDB
        # ChromaDB automatically creates embeddings using its default model
        print(f" Adding {len(documents)} documents to ChromaDB...")
        
        for idx, doc in enumerate(documents):
            try:
                self.collection.add(
                    ids=[f"{doc['metadata']['source']}_{doc['metadata']['chunk_index']}_{idx}"],
                    documents=[doc["content"]],
                    metadatas=[doc["metadata"]]
                )
                
                if (idx + 1) % 10 == 0:
                    print(f" Indexed {idx + 1}/{len(documents)} documents")
            
            except Exception as e:
                print(f" Error indexing document {idx}: {e}")
        
        print(f" Indexing complete! Total documents: {len(documents)}")
        return True
    
    def search(self, query: str, num_results: int = 3) -> List[dict]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            num_results: Number of results to return
        
        Returns:
            List of relevant documents with scores
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=num_results
            )
            
            # Format results
            documents = []
            if results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if results["distances"] else 0
                    })
            
            return documents
        
        except Exception as e:
            print(f" Search error: {e}")
            return []
    
    def get_collection_info(self) -> dict:
        """Get information about the collection"""
        return {
            "collection_name": self.collection_name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata
        }


# Global instance
vector_store = VectorStore()
