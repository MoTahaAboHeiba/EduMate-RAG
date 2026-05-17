#!/usr/bin/env python3
"""
RAG Evaluation Metrics Calculator
==================================
Senior AI Engineer Implementation

Purpose:
    Calculate comprehensive metrics for RAG evaluation.
    Measures retrieval quality, generation quality, and performance.

Author: AI Engineering Team
Version: 1.0.0
"""

import json
import time
from typing import List, Dict, Tuple, Any
from pathlib import Path
import numpy as np
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod


@dataclass
class RetrievalMetrics:
    """Retrieval performance metrics."""
    precision_at_3: float
    precision_at_5: float
    recall_at_5: float
    mrr: float  # Mean Reciprocal Rank
    ndcg_at_10: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class GenerationMetrics:
    """Generation quality metrics."""
    faithfulness_score: float  # 0-1: answers grounded in sources
    relevance_score: float      # 0-1: answers address question
    completeness_score: float   # 0-1: sufficient information
    source_accuracy: float      # 0-1: sources contain answer
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_qps: float
    memory_usage_mb: float
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvaluationResult:
    """Complete evaluation result."""
    question_id: str
    question: str
    retrieved_docs: List[str]
    generated_answer: str
    ground_truth_docs: List[str]
    retrieval_metrics: RetrievalMetrics
    generation_metrics: GenerationMetrics
    performance_metrics: PerformanceMetrics
    
    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "retrieved_docs": self.retrieved_docs,
            "generated_answer": self.generated_answer,
            "ground_truth_docs": self.ground_truth_docs,
            "retrieval_metrics": self.retrieval_metrics.to_dict(),
            "generation_metrics": self.generation_metrics.to_dict(),
            "performance_metrics": self.performance_metrics.to_dict(),
        }


class MetricsCalculator(ABC):
    """Abstract base class for metrics calculators."""
    
    @abstractmethod
    def calculate(self, *args, **kwargs) -> float:
        pass


class PrecisionRecallCalculator(MetricsCalculator):
    """Calculates precision and recall metrics."""
    
    @staticmethod
    def precision_at_k(retrieved_docs: List[str], 
                      ground_truth_docs: List[str], 
                      k: int) -> float:
        """
        Precision@K: % of top-K retrieved docs that are relevant.
        
        Formula: |{Retrieved} ∩ {Ground Truth}| / K
        """
        if k == 0:
            return 0.0
        
        top_k = retrieved_docs[:k]
        relevant = sum(1 for doc in top_k if doc in ground_truth_docs)
        return relevant / k
    
    @staticmethod
    def recall_at_k(retrieved_docs: List[str], 
                   ground_truth_docs: List[str], 
                   k: int) -> float:
        """
        Recall@K: % of all relevant docs found in top-K.
        
        Formula: |{Retrieved} ∩ {Ground Truth}| / |{Ground Truth}|
        """
        if len(ground_truth_docs) == 0:
            return 1.0
        
        top_k = retrieved_docs[:k]
        relevant = sum(1 for doc in top_k if doc in ground_truth_docs)
        return relevant / len(ground_truth_docs)
    
    def calculate(self, retrieved_docs: List[str], 
                  ground_truth_docs: List[str], 
                  k: int) -> Tuple[float, float]:
        """Calculate both precision and recall."""
        precision = self.precision_at_k(retrieved_docs, ground_truth_docs, k)
        recall = self.recall_at_k(retrieved_docs, ground_truth_docs, k)
        return precision, recall


class MeanReciprocalRankCalculator(MetricsCalculator):
    """Calculates Mean Reciprocal Rank."""
    
    @staticmethod
    def mrr(retrieved_docs: List[str], 
            ground_truth_docs: List[str]) -> float:
        """
        MRR: Reciprocal rank of first relevant document.
        
        Formula: 1 / rank_of_first_relevant_doc
        """
        for rank, doc in enumerate(retrieved_docs, 1):
            if doc in ground_truth_docs:
                return 1.0 / rank
        return 0.0
    
    def calculate(self, retrieved_docs: List[str], 
                  ground_truth_docs: List[str]) -> float:
        """Calculate MRR."""
        return self.mrr(retrieved_docs, ground_truth_docs)


class NDCGCalculator(MetricsCalculator):
    """Calculates Normalized Discounted Cumulative Gain."""
    
    @staticmethod
    def dcg_at_k(retrieved_docs: List[str], 
                 ground_truth_docs: List[str], 
                 k: int) -> float:
        """
        DCG@K: Discounted Cumulative Gain
        
        Formula: Σ (relevance_i / log2(i+1))
        """
        dcg = 0.0
        for i, doc in enumerate(retrieved_docs[:k], 1):
            relevance = 1.0 if doc in ground_truth_docs else 0.0
            dcg += relevance / np.log2(i + 1)
        return dcg
    
    @staticmethod
    def ideal_dcg_at_k(num_relevant: int, k: int) -> float:
        """Calculate ideal DCG (perfect ranking)."""
        ideal_dcg = 0.0
        for i in range(min(num_relevant, k)):
            ideal_dcg += 1.0 / np.log2(i + 2)
        return ideal_dcg
    
    @staticmethod
    def ndcg_at_k(retrieved_docs: List[str], 
                  ground_truth_docs: List[str], 
                  k: int) -> float:
        """NDCG@K: Normalized DCG."""
        dcg = NDCGCalculator.dcg_at_k(retrieved_docs, ground_truth_docs, k)
        ideal_dcg = NDCGCalculator.ideal_dcg_at_k(
            len(ground_truth_docs), k
        )
        
        if ideal_dcg == 0:
            return 0.0
        return dcg / ideal_dcg
    
    def calculate(self, retrieved_docs: List[str], 
                  ground_truth_docs: List[str], 
                  k: int) -> float:
        """Calculate NDCG@K."""
        return self.ndcg_at_k(retrieved_docs, ground_truth_docs, k)


class RAGEvaluator:
    """Main RAG evaluation engine."""
    
    def __init__(self):
        """Initialize evaluator with metric calculators."""
        self.pr_calc = PrecisionRecallCalculator()
        self.mrr_calc = MeanReciprocalRankCalculator()
        self.ndcg_calc = NDCGCalculator()
        self.results: List[EvaluationResult] = []
    
    def evaluate_retrieval(self, 
                          retrieved_docs: List[str],
                          ground_truth_docs: List[str]) -> RetrievalMetrics:
        """Evaluate retrieval performance."""
        
        p_3, _ = self.pr_calc.calculate(retrieved_docs, ground_truth_docs, 3)
        p_5, r_5 = self.pr_calc.calculate(retrieved_docs, ground_truth_docs, 5)
        mrr = self.mrr_calc.calculate(retrieved_docs, ground_truth_docs)
        ndcg = self.ndcg_calc.calculate(retrieved_docs, ground_truth_docs, 10)
        
        return RetrievalMetrics(
            precision_at_3=p_3,
            precision_at_5=p_5,
            recall_at_5=r_5,
            mrr=mrr,
            ndcg_at_10=ndcg
        )
    
    def evaluate_generation(self,
                           answer: str,
                           question: str,
                           retrieved_docs: List[str]) -> GenerationMetrics:
        """
        Evaluate generation quality.
        
        Note: These are placeholder implementations.
        In production, use proper LLM-based evaluators or manual scoring.
        """
        
        # Placeholder metrics - these should use proper evaluation
        faithfulness = 0.8  # Typically evaluated by LLM
        relevance = 0.85    # Typically evaluated by LLM
        completeness = 0.75 # Typically evaluated by LLM
        source_accuracy = 0.9  # Based on source validation
        
        return GenerationMetrics(
            faithfulness_score=faithfulness,
            relevance_score=relevance,
            completeness_score=completeness,
            source_accuracy=source_accuracy
        )
    
    def evaluate_performance(self,
                            latencies: List[float]) -> PerformanceMetrics:
        """Evaluate system performance."""
        
        if not latencies:
            latencies = [0.0]
        
        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)
        throughput = 1000 / avg_latency if avg_latency > 0 else 0
        
        return PerformanceMetrics(
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_qps=throughput,
            memory_usage_mb=0.0  # To be measured
        )
    
    def add_result(self, result: EvaluationResult):
        """Add evaluation result."""
        self.results.append(result)
    
    def generate_report(self) -> Dict:
        """Generate comprehensive evaluation report."""
        
        if not self.results:
            return {"error": "No results to report"}
        
        # Aggregate metrics
        retrieval_metrics_list = [r.retrieval_metrics for r in self.results]
        generation_metrics_list = [r.generation_metrics for r in self.results]
        
        avg_retrieval = {
            "avg_precision_at_3": np.mean([m.precision_at_3 for m in retrieval_metrics_list]),
            "avg_precision_at_5": np.mean([m.precision_at_5 for m in retrieval_metrics_list]),
            "avg_recall_at_5": np.mean([m.recall_at_5 for m in retrieval_metrics_list]),
            "avg_mrr": np.mean([m.mrr for m in retrieval_metrics_list]),
            "avg_ndcg_at_10": np.mean([m.ndcg_at_10 for m in retrieval_metrics_list]),
        }
        
        avg_generation = {
            "avg_faithfulness": np.mean([m.faithfulness_score for m in generation_metrics_list]),
            "avg_relevance": np.mean([m.relevance_score for m in generation_metrics_list]),
            "avg_completeness": np.mean([m.completeness_score for m in generation_metrics_list]),
            "avg_source_accuracy": np.mean([m.source_accuracy for m in generation_metrics_list]),
        }
        
        return {
            "num_questions": len(self.results),
            "retrieval_metrics": avg_retrieval,
            "generation_metrics": avg_generation,
            "individual_results": [r.to_dict() for r in self.results]
        }


if __name__ == "__main__":
    # Demo
    evaluator = RAGEvaluator()
    
    # Example
    retrieved = ["doc1", "doc2", "doc3"]
    ground_truth = ["doc1", "doc3"]
    
    retrieval_metrics = evaluator.evaluate_retrieval(retrieved, ground_truth)
    print(f"Precision@3: {retrieval_metrics.precision_at_3:.2f}")
    print(f"Recall@5: {retrieval_metrics.recall_at_5:.2f}")
    print(f"MRR: {retrieval_metrics.mrr:.2f}")
    print(f"NDCG@10: {retrieval_metrics.ndcg_at_10:.2f}")
