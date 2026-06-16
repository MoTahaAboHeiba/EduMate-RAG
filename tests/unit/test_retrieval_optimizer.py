import pytest
from src.core.retrieval_optimizer import RetrievalOptimizer

def test_filter_by_similarity_chroma_distance():
    # Chroma returns distance: lower is better. 
    # similarity = 1 - (distance / 2)
    # doc1 similarity: 1 - 0.2/2 = 0.9
    # doc2 similarity: 1 - 1.2/2 = 0.4
    # doc3 similarity: 1 - 1.8/2 = 0.1
    docs = [
        {"content": "doc1", "distance": 0.2},
        {"content": "doc2", "distance": 1.2},
        {"content": "doc3", "distance": 1.8}
    ]
    
    # Threshold 0.5 should keep doc1 only
    filtered = RetrievalOptimizer.filter_by_similarity(docs, similarity_threshold=0.5)
    assert len(filtered) == 1
    assert filtered[0]["content"] == "doc1"
    assert filtered[0]["similarity"] == 0.9

def test_filter_by_similarity_direct():
    # If similarity is already present (e.g. from Qdrant), use it directly
    docs = [
        {"content": "doc1", "similarity": 0.85},
        {"content": "doc2", "similarity": 0.3},
        {"content": "doc3", "distance": 0.1, "similarity": 0.95}  # should favor similarity key
    ]
    
    filtered = RetrievalOptimizer.filter_by_similarity(docs, similarity_threshold=0.5)
    assert len(filtered) == 2
    # doc3 has higher similarity (0.95) and should be first due to sorting
    assert filtered[0]["content"] == "doc3"
    assert filtered[1]["content"] == "doc1"

def test_rerank_by_relevance_keyword_overlap():
    docs = [
        {"content": "The quick brown fox jumps over the lazy dog"},
        {"content": "Fast sorting algorithms like quicksort and mergesort"},
        {"content": "Nothing in common"}
    ]
    query = "quicksort mergesort algorithms"
    
    reranked = RetrievalOptimizer.rerank_by_relevance(docs, query, method="keyword_overlap")
    # doc 1 (sorting algorithms) has best overlap
    assert reranked[0]["content"] == "Fast sorting algorithms like quicksort and mergesort"
    assert reranked[0]["relevance_score"] > 0

def test_deduplicate_documents():
    docs = [
        {"content": "The quick brown fox jumps over the lazy dog"},
        {"content": "The quick brown fox jumps over the lazy dog"},  # exact duplicate
        {"content": "A completely different sentence"}
    ]
    
    deduped = RetrievalOptimizer.deduplicate_documents(docs, threshold=0.8)
    assert len(deduped) == 2
    assert deduped[0]["content"] == "The quick brown fox jumps over the lazy dog"
    assert deduped[1]["content"] == "A completely different sentence"

def test_optimize_retrieval_full():
    docs = [
        {"content": "The quick brown fox jumps over the lazy dog", "similarity": 0.9},
        {"content": "The quick brown fox jumps over the lazy dog", "similarity": 0.85},  # duplicate
        {"content": "Low similarity noise", "similarity": 0.1}
    ]
    
    result = RetrievalOptimizer.optimize_retrieval(
        documents=docs,
        query="quick brown fox",
        top_k=2,
        enable_dedup=True,
        enable_rerank=True,
        similarity_threshold=0.3
    )
    
    # Duplicate should be removed, noise filtered, top_k limited to 2
    assert len(result) == 1
    assert result[0]["content"] == "The quick brown fox jumps over the lazy dog"
