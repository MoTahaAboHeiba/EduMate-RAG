"""
Embedding cache for reducing re-computation of embeddings.
Stores precomputed embeddings to avoid redundant calculations.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional


class EmbeddingCache:
    """Cache for storing and retrieving precomputed embeddings."""
    
    def __init__(self, cache_dir: Path = None):
        """
        Initialize embedding cache.
        
        Args:
            cache_dir: Directory to store embedding cache
        """
        if cache_dir is None:
            cache_dir = Path(".cache") / "embeddings"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self.embeddings_cache = self._load_cache()
    
    def _hash_text(self, text: str) -> str:
        """
        Create hash of text for cache key.
        
        Args:
            text: Text to hash
            
        Returns:
            SHA256 hash of text
        """
        return hashlib.sha256(text.encode()).hexdigest()
    
    def _load_cache(self) -> Dict[str, List[float]]:
        """Load embedding cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load embedding cache: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Save embedding cache to disk."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.embeddings_cache, f)
        except Exception as e:
            print(f"Failed to save embedding cache: {e}")
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for text.
        
        Args:
            text: Text to look up
            
        Returns:
            Cached embedding if available, None otherwise
        """
        text_hash = self._hash_text(text)
        return self.embeddings_cache.get(text_hash)
    
    def get_batch(self, texts: List[str]) -> tuple:
        """
        Retrieve embeddings for batch of texts.
        
        Args:
            texts: List of texts to look up
            
        Returns:
            Tuple of (embeddings_found, missing_indices, missing_texts)
        """
        embeddings_found = [None] * len(texts)
        missing_indices = []
        missing_texts = []
        
        for idx, text in enumerate(texts):
            cached = self.get(text)
            if cached is not None:
                embeddings_found[idx] = cached
            else:
                missing_indices.append(idx)
                missing_texts.append(text)
        
        return embeddings_found, missing_indices, missing_texts
    
    def set(self, text: str, embedding: List[float]):
        """
        Cache embedding for text.
        
        Args:
            text: Text to cache
            embedding: Embedding vector
        """
        text_hash = self._hash_text(text)
        self.embeddings_cache[text_hash] = embedding
    
    def set_batch(self, texts: List[str], embeddings: List[List[float]]):
        """
        Cache batch of embeddings.
        
        Args:
            texts: List of texts
            embeddings: List of embedding vectors
        """
        for text, embedding in zip(texts, embeddings):
            self.set(text, embedding)
        self._save_cache()
    
    def clear(self):
        """Clear all cached embeddings."""
        self.embeddings_cache = {}
        self._save_cache()
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "total_cached": len(self.embeddings_cache),
            "cache_file": str(self.cache_file),
            "cache_size_bytes": self.cache_file.stat().st_size if self.cache_file.exists() else 0
        }


embedding_cache = EmbeddingCache()
