"""
Retrieval Optimizer - Advanced techniques to improve precision and reduce noise
"""
from typing import List, Dict, Tuple
import math


class RetrievalOptimizer:
    """
    Advanced retrieval optimization techniques:
    - Similarity filtering
    - Result reranking
    - Diversity scoring
    - Relevance boosting
    """
    
    @staticmethod
    def filter_by_similarity(
        documents: List[dict], 
        similarity_threshold: float = 0.5
    ) -> List[dict]:
        """
        Filter documents by similarity score (distance).
        Lower distance = higher similarity.
        
        Args:
            documents: List of retrieved documents with 'distance' field
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            Filtered list of relevant documents
        """
        if not documents:
            return documents
        
        filtered = []
        for doc in documents:
            # ChromaDB returns distance; convert to similarity (cosine: lower is better)
            # For cosine distance in range [0, 2], convert to similarity: 1 - distance/2
            distance = doc.get('distance', 0)
            similarity = 1 - (distance / 2) if distance <= 2 else 0
            
            if similarity >= similarity_threshold:
                doc['similarity'] = similarity
                filtered.append(doc)
        
        # Sort by similarity descending
        filtered.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return filtered
    
    @staticmethod
    def rerank_by_relevance(
        documents: List[dict],
        query: str,
        method: str = 'keyword_overlap'
    ) -> List[dict]:
        """
        Rerank documents using relevance scoring.
        Better documents bubble to top.
        
        Args:
            documents: List of retrieved documents
            query: Original query/question
            method: Reranking method ('keyword_overlap', 'content_length', 'combined')
            
        Returns:
            Reranked list of documents
        """
        if not documents:
            return documents
        
        if method == 'keyword_overlap':
            # Score based on query keyword overlap in content
            query_keywords = set(word.lower() for word in query.split() if len(word) > 3)
            
            for doc in documents:
                content = doc['content'].lower()
                overlap = sum(1 for kw in query_keywords if kw in content)
                doc['relevance_score'] = overlap / max(len(query_keywords), 1)
        
        elif method == 'content_length':
            # Prefer medium-length content (not too short, not too long noise)
            for doc in documents:
                content_len = len(doc['content'])
                # Sweet spot: 200-500 tokens
                if 150 <= content_len <= 1000:
                    doc['relevance_score'] = 1.0
                elif 100 <= content_len <= 1500:
                    doc['relevance_score'] = 0.8
                else:
                    doc['relevance_score'] = 0.5
        
        elif method == 'combined':
            # Combine similarity and keyword overlap
            query_keywords = set(word.lower() for word in query.split() if len(word) > 3)
            
            for doc in documents:
                # Keyword overlap score
                content = doc['content'].lower()
                keyword_score = sum(1 for kw in query_keywords if kw in content) / max(len(query_keywords), 1)
                
                # Similarity score (if available)
                similarity = doc.get('similarity', 0.5)
                
                # Combined: weighted average
                doc['relevance_score'] = 0.6 * similarity + 0.4 * keyword_score
        
        # Sort by relevance score descending
        documents.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return documents
    
    @staticmethod
    def deduplicate_documents(
        documents: List[dict],
        threshold: float = 0.9
    ) -> List[dict]:
        """
        Remove near-duplicate documents based on content similarity.
        Keeps the highest-ranked document and removes similar ones.
        
        Args:
            documents: List of ranked documents
            threshold: Similarity threshold for considering as duplicate (0-1)
            
        Returns:
            Deduplicated list
        """
        if len(documents) <= 1:
            return documents
        
        unique_docs = []
        
        for doc in documents:
            is_duplicate = False
            doc_tokens = set(doc['content'].lower().split())
            
            for unique_doc in unique_docs:
                unique_tokens = set(unique_doc['content'].lower().split())
                
                # Jaccard similarity
                if len(doc_tokens | unique_tokens) > 0:
                    jaccard = len(doc_tokens & unique_tokens) / len(doc_tokens | unique_tokens)
                    if jaccard >= threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_docs.append(doc)
        
        return unique_docs
    
    @staticmethod
    def select_top_k(
        documents: List[dict],
        k: int = 3
    ) -> List[dict]:
        """
        Select top K documents, assuming they're already ranked.
        
        Args:
            documents: Ranked list of documents
            k: Number of documents to keep
            
        Returns:
            Top K documents
        """
        return documents[:k]
    
    @staticmethod
    def optimize_retrieval(
        documents: List[dict],
        query: str,
        top_k: int = 3,
        enable_dedup: bool = True,
        enable_rerank: bool = True,
        similarity_threshold: float = 0.0
    ) -> List[dict]:
        """
        Full optimization pipeline for retrieved documents.
        
        Steps:
        1. Filter by similarity threshold
        2. Rerank by relevance
        3. Deduplicate
        4. Select top-k
        
        Args:
            documents: Retrieved documents from vector store
            query: Original query
            top_k: Number of final documents to keep
            enable_dedup: Whether to deduplicate
            enable_rerank: Whether to rerank
            similarity_threshold: Minimum similarity to keep
            
        Returns:
            Optimized top-k documents
        """
        if not documents:
            return documents
        
        # Step 1: Filter by similarity
        if similarity_threshold > 0:
            documents = RetrievalOptimizer.filter_by_similarity(
                documents, 
                similarity_threshold
            )
            print(f"   [Optimizer] After similarity filtering: {len(documents)} docs")
        
        # Step 2: Rerank
        if enable_rerank and len(documents) > 0:
            documents = RetrievalOptimizer.rerank_by_relevance(
                documents,
                query,
                method='combined'
            )
            print(f"   [Optimizer] After reranking: kept {len(documents)} docs")
        
        # Step 3: Deduplicate
        if enable_dedup and len(documents) > 1:
            documents = RetrievalOptimizer.deduplicate_documents(documents, threshold=0.85)
            print(f"   [Optimizer] After deduplication: {len(documents)} unique docs")
        
        # Step 4: Select top-k
        documents = RetrievalOptimizer.select_top_k(documents, k=top_k)
        
        return documents


# Global instance
retrieval_optimizer = RetrievalOptimizer()
