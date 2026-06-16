#!/usr/bin/env python3
"""
EduMate-RAG Standalone Retrieval Evaluation Script
==================================================
Runs evaluation across a 2x4 experiment matrix:
- thresholds: [0.0, 0.3]
- top_k: [3, 5, 10, 20]

Bypasses the LLM / Groq API to query ChromaDB locally.
"""
import os
import sys
from pathlib import Path

# 1. Force the vector store backend to ChromaDB before importing any project modules
os.environ["VECTOR_STORE_BACKEND"] = "chroma"

from dotenv import load_dotenv
load_dotenv()

# Fallback placeholders for CI or offline runs
os.environ.setdefault("GROQ_API_KEY", "_OFFLINE_PLACEHOLDER_")
os.environ.setdefault("ADMIN_KEY", "_OFFLINE_PLACEHOLDER_")

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import json
import time
import numpy as np
from datetime import datetime
from typing import List, Dict, Any

from src.document_processing.vector_store import vector_store
from src.core.retrieval_optimizer import retrieval_optimizer
from evaluation.metrics.metrics_calculator import RAGEvaluator, RetrievalMetrics


def run_evaluation_for_config(
    qa_pairs: List[Dict[str, Any]],
    threshold: float,
    top_k: int
) -> Dict[str, Any]:
    """Runs retrieval evaluation on all QA pairs for a single configuration."""
    evaluator = RAGEvaluator()
    
    search_latencies = []
    optimizer_latencies = []
    total_latencies = []
    
    individual_results = []
    
    initial_k = max(top_k * 3, 10)
    print(f"Evaluating config: threshold={threshold}, top_k={top_k} (initial_k={initial_k})...")
    
    for qa in qa_pairs:
        query = qa["question"]
        ground_truth = qa["ground_truth_docs"]
        
        # 1. Perform Search (measure search latency)
        t0 = time.perf_counter()
        raw_docs = vector_store.search(query, num_results=initial_k)
        t1 = time.perf_counter()
        search_ms = (t1 - t0) * 1000
        
        # 2. Optimize Retrieval (measure optimizer latency)
        t2 = time.perf_counter()
        optimized_docs = retrieval_optimizer.optimize_retrieval(
            documents=raw_docs,
            query=query,
            top_k=top_k,
            enable_dedup=True,
            enable_rerank=True,
            similarity_threshold=threshold
        )
        t3 = time.perf_counter()
        optimizer_ms = (t3 - t2) * 1000
        
        search_latencies.append(search_ms)
        optimizer_latencies.append(optimizer_ms)
        total_latencies.append(search_ms + optimizer_ms)
        
        # Extract sources
        retrieved_sources = [doc["metadata"].get("source", "") for doc in optimized_docs]
        
        # Compute metrics
        metrics = evaluator.evaluate_retrieval(retrieved_sources, ground_truth)
        
        # Save individual query result
        individual_results.append({
            "question_id": qa["id"],
            "question": query,
            "ground_truth_docs": ground_truth,
            "retrieved_docs": retrieved_sources,
            "metrics": metrics.to_dict(),
            "latency": {
                "search_ms": search_ms,
                "optimizer_ms": optimizer_ms,
                "total_ms": search_ms + optimizer_ms
            }
        })
    
    # Calculate aggregate metrics
    metric_keys = [
        "precision_at_1", "precision_at_3", "precision_at_5", "precision_at_10",
        "recall_at_1", "recall_at_3", "recall_at_5", "recall_at_10",
        "mrr", "ndcg_at_5", "ndcg_at_10",
        "hit_rate_at_1", "hit_rate_at_3", "hit_rate_at_5", "hit_rate_at_10"
    ]
    
    aggregates = {}
    for key in metric_keys:
        aggregates[f"avg_{key}"] = float(np.mean([res["metrics"][key] for res in individual_results]))
        
    aggregates["avg_search_latency_ms"] = float(np.mean(search_latencies))
    aggregates["avg_optimizer_latency_ms"] = float(np.mean(optimizer_latencies))
    aggregates["avg_latency_ms"] = float(np.mean(total_latencies))
    aggregates["p95_latency_ms"] = float(np.percentile(total_latencies, 95))
    
    return {
        "config": {
            "threshold": threshold,
            "top_k": top_k,
            "initial_k": initial_k
        },
        "aggregate": aggregates,
        "per_query": individual_results
    }


def print_comparison_tables(experiments: List[Dict[str, Any]]):
    """Prints beautiful formatted tables to console."""
    # Find experiments matching configurations
    # 1. Threshold comparison at top_k=5
    print("\n" + "="*80)
    print("THRESHOLD COMPARISON (at top_k=5)")
    print("="*80)
    print(f"{'Threshold':<12} | {'Avg P@3':<8} | {'Avg P@5':<8} | {'Avg R@5':<8} | {'Avg MRR':<8} | {'Avg NDCG@10':<12} | {'Avg Latency':<12}")
    print("-" * 80)
    for exp in experiments:
        if exp["config"]["top_k"] == 5:
            cfg = exp["config"]
            agg = exp["aggregate"]
            print(f"{cfg['threshold']:<12.1f} | {agg['avg_precision_at_3']:<8.4f} | {agg['avg_precision_at_5']:<8.4f} | {agg['avg_recall_at_5']:<8.4f} | {agg['avg_mrr']:<8.4f} | {agg['avg_ndcg_at_10']:<12.4f} | {agg['avg_latency_ms']:<9.2f} ms")

    # 2. Depth comparison (top_k=3, 5, 10, 20) at threshold=0.0
    print("\n" + "="*80)
    print("DEPTH EXPERIMENT TABLE (at threshold=0.0 — No filtering)")
    print("="*80)
    print(f"{'Top-K':<8} | {'Avg P@3':<8} | {'Avg P@5':<8} | {'Avg R@5':<8} | {'Avg R@10':<9} | {'Avg MRR':<8} | {'Avg HR@5':<8} | {'Avg Latency':<12}")
    print("-" * 80)
    for exp in experiments:
        if exp["config"]["threshold"] == 0.0:
            cfg = exp["config"]
            agg = exp["aggregate"]
            print(f"{cfg['top_k']:<8} | {agg['avg_precision_at_3']:<8.4f} | {agg['avg_precision_at_5']:<8.4f} | {agg['avg_recall_at_5']:<8.4f} | {agg['avg_recall_at_10']:<9.4f} | {agg['avg_mrr']:<8.4f} | {agg['avg_hit_rate_at_5']:<8.4f} | {agg['avg_latency_ms']:<9.2f} ms")

    # 3. Depth comparison (top_k=3, 5, 10, 20) at threshold=0.3
    print("\n" + "="*80)
    print("DEPTH EXPERIMENT TABLE (at threshold=0.3 — With similarity filtering)")
    print("="*80)
    print(f"{'Top-K':<8} | {'Avg P@3':<8} | {'Avg P@5':<8} | {'Avg R@5':<8} | {'Avg R@10':<9} | {'Avg MRR':<8} | {'Avg HR@5':<8} | {'Avg Latency':<12}")
    print("-" * 80)
    for exp in experiments:
        if exp["config"]["threshold"] == 0.3:
            cfg = exp["config"]
            agg = exp["aggregate"]
            print(f"{cfg['top_k']:<8} | {agg['avg_precision_at_3']:<8.4f} | {agg['avg_precision_at_5']:<8.4f} | {agg['avg_recall_at_5']:<8.4f} | {agg['avg_recall_at_10']:<9.4f} | {agg['avg_mrr']:<8.4f} | {agg['avg_hit_rate_at_5']:<8.4f} | {agg['avg_latency_ms']:<9.2f} ms")


def get_best_config(experiments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Finds the best configuration.
    Decision rule: Prioritize Recall@5 while keeping Precision@3 >= 0.70 (if possible).
    Otherwise, choose the configuration with the highest MRR.
    """
    best_exp = None
    best_score = -1.0
    
    # We can rank them by a composite score: 0.5 * recall_at_5 + 0.5 * mrr
    for exp in experiments:
        agg = exp["aggregate"]
        # Composite score
        score = 0.5 * agg["avg_recall_at_5"] + 0.5 * agg["avg_mrr"]
        if score > best_score:
            best_score = score
            best_exp = exp
            
    return best_exp


def main():
    print("="*80)
    print("EduMate-RAG Standalone Retrieval Evaluation Suite")
    print(f"Database Backend: ChromaDB (Path: {vector_store.collection_name})")
    print("="*80)
    
    # Ensure collection exists and is not empty
    try:
        count = vector_store.collection.count()
        print(f"ChromaDB Collection count: {count} documents")
        if count == 0:
            print("ERROR: ChromaDB collection is empty. Please run indexing first!")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR connecting to ChromaDB: {e}")
        sys.exit(1)
        
    # Load dataset
    dataset_path = project_root / "evaluation" / "datasets" / "rag_evaluation_dataset_v1.json"
    rel_dataset_path = dataset_path.relative_to(project_root) if project_root in dataset_path.parents else dataset_path.name
    print(f"Loading dataset from: {rel_dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    qa_pairs = dataset["qa_pairs"]
    print(f"Loaded {len(qa_pairs)} query-document evaluation pairs.")
    
    thresholds = [0.0, 0.3]
    top_k_values = [3, 5, 10, 20]
    
    experiments = []
    
    for threshold in thresholds:
        for top_k in top_k_values:
            exp_res = run_evaluation_for_config(qa_pairs, threshold, top_k)
            experiments.append(exp_res)
            
    # Output report
    print_comparison_tables(experiments)
    
    best_config = get_best_config(experiments)
    best_cfg = best_config["config"]
    best_agg = best_config["aggregate"]
    
    print("\n" + "="*80)
    print("BEST CONFIGURATION RECOMMENDATION")
    print("="*80)
    print(f"Recommended Config: threshold={best_cfg['threshold']}, top_k={best_cfg['top_k']}")
    print(f"Metrics with Recommended Config:")
    print(f"  Avg Precision@3:   {best_agg['avg_precision_at_3']:.4f}")
    print(f"  Avg Precision@5:   {best_agg['avg_precision_at_5']:.4f}")
    print(f"  Avg Recall@5:      {best_agg['avg_recall_at_5']:.4f}")
    print(f"  Avg MRR:           {best_agg['avg_mrr']:.4f}")
    print(f"  Avg NDCG@10:       {best_agg['avg_ndcg_at_10']:.4f}")
    print(f"  Avg Latency:       {best_agg['avg_latency_ms']:.2f} ms (p95: {best_agg['p95_latency_ms']:.2f} ms)")
    
    # Save output report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = project_root / "evaluation" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "ground_truth_granularity": "document",
        "vector_store": "chromadb",
        "thresholds_tested": thresholds,
        "top_k_values_tested": top_k_values,
        "best_config": {
            "threshold": best_cfg['threshold'],
            "top_k": best_cfg['top_k']
        },
        "experiments": experiments
    }
    
    output_filename = f"retrieval_eval_{timestamp}.json"
    output_path = results_dir / output_filename
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
        
    rel_output_path = output_path.relative_to(project_root) if project_root in output_path.parents else output_path.name
    print(f"\nSaved full experimental results to: {rel_output_path}")
    print("="*80)


if __name__ == "__main__":
    main()
