#!/usr/bin/env python3
"""
PHASE 3: INFERENCE & METRICS CALCULATION
=========================================
Run RAG system against evaluation dataset and calculate metrics.

Author: AI Engineering Team
Version: 1.0.0
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
import requests
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from evaluation.metrics.metrics_calculator import RAGEvaluator, EvaluationResult, RetrievalMetrics, GenerationMetrics, PerformanceMetrics


class Phase3Executor:
    """Execute Phase 3: Inference and Metrics Calculation"""
    
    def __init__(self):
        self.evaluation_dir = Path(__file__).parent
        self.dataset_path = self.evaluation_dir / "datasets" / "rag_evaluation_dataset_v1.json"
        self.results_dir = self.evaluation_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.api_base_url = "http://localhost:8000"
        self.evaluator = RAGEvaluator()
        self.results = []
        self.latencies = []
        
    def load_dataset(self) -> List[Dict]:
        """Load evaluation dataset"""
        print("\n[STEP 1] Loading Evaluation Dataset")
        print("=" * 70)
        
        with open(self.dataset_path, encoding='utf-8') as f:
            data = json.load(f)
        
        qa_pairs = data["qa_pairs"]
        print(f"Loaded {len(qa_pairs)} QA pairs")
        return qa_pairs
    
    def check_api_health(self):
        """Verify RAG API is running"""
        print("\n[STEP 2] Checking RAG API Health")
        print("=" * 70)
        
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                print("API Status: OK (200)")
                data = response.json()
                print(f"Model: {data.get('model', 'N/A')}")
                print(f"Documents indexed: {data.get('vector_store', {}).get('documents_indexed', 'N/A')}")
                return True
        except Exception as e:
            print(f"ERROR: Cannot connect to API at {self.api_base_url}")
            print(f"Make sure to run: python src/api/main.py")
            return False
    
    def query_rag_system(self, question: str) -> Dict[str, Any]:
        """Query RAG system and get answer"""
        try:
            response = requests.post(
                f"{self.api_base_url}/api/query",
                json={"question": question},
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            print("Query timeout (60s)")
            return None
        except Exception as e:
            print(f"Query error: {e}")
            return None
    
    def evaluate_query(self, qa_pair: Dict, query_result: Dict, latency_ms: float) -> EvaluationResult:
        """Evaluate a single query result"""
        
        question = qa_pair["question"]
        ground_truth_docs = qa_pair["ground_truth_docs"]
        generated_answer = query_result.get("answer", "")
        retrieved_docs = query_result.get("sources", [])
        
        # Calculate retrieval metrics
        retrieval_metrics = self.evaluator.evaluate_retrieval(
            retrieved_docs, ground_truth_docs
        )
        
        # Calculate generation metrics
        generation_metrics = self.evaluator.evaluate_generation(
            generated_answer, question, retrieved_docs
        )
        
        # Performance metrics
        performance_metrics = PerformanceMetrics(
            avg_latency_ms=latency_ms,
            p95_latency_ms=latency_ms,
            p99_latency_ms=latency_ms,
            throughput_qps=1000.0 / latency_ms if latency_ms > 0 else 0,
            memory_usage_mb=0.0
        )
        
        result = EvaluationResult(
            question_id=qa_pair["id"],
            question=question,
            retrieved_docs=retrieved_docs,
            generated_answer=generated_answer,
            ground_truth_docs=ground_truth_docs,
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics,
            performance_metrics=performance_metrics
        )
        
        return result
    
    def run_evaluation(self, qa_pairs: List[Dict]):
        """Run evaluation on all QA pairs"""
        print("\n[STEP 3] Running Inference & Metrics Calculation")
        print("=" * 70)
        
        total = len(qa_pairs)
        
        for idx, qa_pair in enumerate(qa_pairs, 1):
            question = qa_pair["question"]
            
            # Show progress - sanitize for console output
            safe_question = question[:50].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            status = f"[{idx:3d}/{total}] Processing: {safe_question}..."
            try:
                print(status, end=' ', flush=True)
            except UnicodeEncodeError:
                print(f"[{idx:3d}/{total}] Processing: [Q{idx}]...", end=' ', flush=True)
            
            # Query RAG system and measure latency
            start_time = time.time()
            query_result = self.query_rag_system(question)
            latency_ms = (time.time() - start_time) * 1000
            self.latencies.append(latency_ms)
            
            if query_result:
                result = self.evaluate_query(qa_pair, query_result, latency_ms)
                self.results.append(result)
                print(f"OK ({latency_ms:.0f}ms)")
            else:
                print("FAILED")
        
        print(f"\nSuccessfully evaluated: {len(self.results)}/{total}")
    
    def aggregate_results(self) -> Dict:
        """Aggregate all results"""
        print("\n[STEP 4] Aggregating Results")
        print("=" * 70)
        
        if not self.results:
            print("No results to aggregate")
            return {}
        
        retrieval_metrics = [r.retrieval_metrics for r in self.results]
        generation_metrics = [r.generation_metrics for r in self.results]
        
        import numpy as np
        
        aggregated = {
            "num_queries": len(self.results),
            "retrieval": {
                "avg_precision_at_3": float(np.mean([m.precision_at_3 for m in retrieval_metrics])),
                "avg_precision_at_5": float(np.mean([m.precision_at_5 for m in retrieval_metrics])),
                "avg_recall_at_5": float(np.mean([m.recall_at_5 for m in retrieval_metrics])),
                "avg_mrr": float(np.mean([m.mrr for m in retrieval_metrics])),
                "avg_ndcg_at_10": float(np.mean([m.ndcg_at_10 for m in retrieval_metrics])),
            },
            "generation": {
                "avg_faithfulness": float(np.mean([m.faithfulness_score for m in generation_metrics])),
                "avg_relevance": float(np.mean([m.relevance_score for m in generation_metrics])),
                "avg_completeness": float(np.mean([m.completeness_score for m in generation_metrics])),
                "avg_source_accuracy": float(np.mean([m.source_accuracy for m in generation_metrics])),
            },
            "performance": {
                "avg_latency_ms": float(np.mean(self.latencies)),
                "p95_latency_ms": float(np.percentile(self.latencies, 95)),
                "p99_latency_ms": float(np.percentile(self.latencies, 99)),
                "throughput_qps": float(1000.0 / np.mean(self.latencies)) if self.latencies else 0,
            }
        }
        
        print(f"Average Latency: {aggregated['performance']['avg_latency_ms']:.0f}ms")
        print(f"Average Precision@3: {aggregated['retrieval']['avg_precision_at_3']:.2%}")
        print(f"Average Recall@5: {aggregated['retrieval']['avg_recall_at_5']:.2%}")
        
        return aggregated
    
    def save_results(self, aggregated: Dict):
        """Save all results to files"""
        print("\n[STEP 5] Saving Results")
        print("=" * 70)
        
        # Save individual results
        results_data = {
            "timestamp": self.timestamp,
            "total_queries": len(self.results),
            "results": [r.to_dict() for r in self.results]
        }
        
        results_file = self.results_dir / f"phase3_results_{self.timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        print(f"Individual results: {results_file}")
        
        # Save aggregated metrics
        aggregated_file = self.results_dir / f"phase3_aggregated_{self.timestamp}.json"
        with open(aggregated_file, 'w') as f:
            json.dump(aggregated, f, indent=2)
        print(f"Aggregated metrics: {aggregated_file}")
        
        return results_file, aggregated_file
    
    def run(self):
        """Execute Phase 3"""
        print("\n" + "="*70)
        print("PHASE 3: INFERENCE & METRICS CALCULATION")
        print("="*70)
        
        try:
            # Step 1: Load dataset
            qa_pairs = self.load_dataset()
            
            # Step 2: Check API
            if not self.check_api_health():
                print("\nERROR: Cannot proceed without running RAG API")
                print("Run in another terminal: python src/api/main.py")
                return False
            
            # Step 3: Run evaluation
            self.run_evaluation(qa_pairs)
            
            # Step 4: Aggregate
            aggregated = self.aggregate_results()
            
            # Step 5: Save
            self.save_results(aggregated)
            
            print("\n" + "="*70)
            print("PHASE 3 COMPLETE")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    executor = Phase3Executor()
    success = executor.run()
    sys.exit(0 if success else 1)
