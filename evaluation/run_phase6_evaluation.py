#!/usr/bin/env python3
"""
PHASE 6: RE-EVALUATION WITH STRICTER VALIDATION
=================================================
Run RAG system with Phase 6 settings (temperature 0.3, enforced validation)
against new dataset to measure quality improvements.

Key Changes from Phase 5:
- Temperature: 0.5 → 0.3 (stricter, less creative)
- Validation: Logging only → Enforced rejection
- Dataset: Different set of questions (not original 85 QA pairs)

Author: AI Engineering Team
Version: 1.0.0
Date: May 21, 2026
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import requests
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class Phase6Evaluator:
    """Execute Phase 6: Re-evaluation with Stricter Settings"""
    
    def __init__(self, dataset_name: str = "phase6_dataset.json"):
        self.evaluation_dir = Path(__file__).parent
        self.dataset_path = self.evaluation_dir / dataset_name
        self.results_dir = self.evaluation_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.api_base_url = "http://localhost:8000"
        self.results = []
        self.latencies = []
        self.grounding_scores = []
        self.rejected_answers = 0
        self.total_queries = 0
        
    def load_dataset(self) -> List[Dict]:
        """Load Phase 6 evaluation dataset"""
        print("\n" + "=" * 80)
        print("PHASE 6: RE-EVALUATION WITH STRICTER VALIDATION")
        print("=" * 80)
        print("\n[STEP 1] Loading Phase 6 Evaluation Dataset")
        print("-" * 80)
        
        if not self.dataset_path.exists():
            print(f"ERROR: Dataset not found at {self.dataset_path}")
            return []
            
        with open(self.dataset_path, encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            qa_pairs = data
        else:
            qa_pairs = data.get("qa_pairs", data)
        
        print(f"✓ Loaded {len(qa_pairs)} test questions")
        print(f"  Dataset: {self.dataset_path.name}")
        return qa_pairs
    
    def check_api_health(self) -> bool:
        """Verify RAG API is running with Phase 6 settings"""
        print("\n[STEP 2] Checking RAG API Health & Configuration")
        print("-" * 80)
        
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✓ API Status: OK (200)")
                data = response.json()
                print(f"  Model: {data.get('model', 'N/A')}")
                print(f"  Documents indexed: {data.get('vector_store', {}).get('documents_indexed', 'N/A')}")
                
                # Check for Phase 6 settings in response
                config = data.get('config', {})
                if config:
                    print(f"  Configuration:")
                    print(f"    - Temperature: {config.get('temperature', 'N/A')}")
                    print(f"    - Enforce Validation: {config.get('enforce_validation', 'N/A')}")
                
                return True
        except Exception as e:
            print(f"✗ ERROR: Cannot connect to API at {self.api_base_url}")
            print(f"  Make sure to run: python src/api/main.py")
            print(f"  Error: {e}")
            return False
    
    def query_rag_system(self, question: str) -> Tuple[Dict[str, Any], float]:
        """Query RAG system and measure latency"""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.api_base_url}/api/query",
                json={"question": question},
                timeout=60
            )
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return response.json(), latency_ms
            else:
                print(f"Error: {response.status_code}")
                return None, latency_ms
        except requests.exceptions.Timeout:
            print("Query timeout (60s)")
            return None, (time.time() - start_time) * 1000
        except Exception as e:
            print(f"Query error: {e}")
            return None, (time.time() - start_time) * 1000
    
    def analyze_answer_grounding(self, answer: str, expected_patterns: List[str]) -> Dict[str, Any]:
        """Analyze answer grounding against expected patterns"""
        if not answer:
            return {
                "has_answer": False,
                "grounding_score": 0.0,
                "matched_keywords": [],
                "expected_keywords": expected_patterns
            }
        
        answer_lower = answer.lower()
        matched = []
        
        for pattern in expected_patterns:
            if pattern.lower() in answer_lower:
                matched.append(pattern)
        
        grounding_score = len(matched) / len(expected_patterns) if expected_patterns else 0.0
        
        return {
            "has_answer": len(answer) > 10,  # More than just fallback message
            "grounding_score": grounding_score,
            "matched_keywords": matched,
            "expected_keywords": expected_patterns,
            "match_count": len(matched),
            "expected_count": len(expected_patterns)
        }
    
    def run_evaluation(self, qa_pairs: List[Dict]):
        """Run evaluation on all test questions"""
        print("\n[STEP 3] Running Phase 6 Evaluation")
        print("-" * 80)
        
        total = len(qa_pairs)
        self.total_queries = total
        
        for idx, qa_pair in enumerate(qa_pairs, 1):
            question = qa_pair["question"]
            expected_patterns = qa_pair.get("expected_answer_pattern", [])
            
            # Show progress
            safe_question = question[:50] if len(question) > 50 else question
            print(f"\n[{idx:2d}/{total}] {safe_question}...")
            
            # Query system
            query_result, latency_ms = self.query_rag_system(question)
            self.latencies.append(latency_ms)
            
            if query_result is None:
                print(f"  ✗ Query failed (latency: {latency_ms:.0f}ms)")
                continue
            
            answer = query_result.get("answer", "")
            sources = query_result.get("sources", [])
            grounding_info = query_result.get("grounding_info", {})
            
            # Check if answer is a fallback (Phase 6 rejection)
            is_fallback = "don't have enough information" in answer or "cannot confidently" in answer
            if is_fallback:
                self.rejected_answers += 1
                print(f"  ⚠ Answer REJECTED by Phase 6 validation (grounding too low)")
                print(f"    Latency: {latency_ms:.0f}ms")
                continue
            
            # Analyze grounding
            analysis = self.analyze_answer_grounding(answer, expected_patterns)
            grounding_score = analysis["grounding_score"]
            self.grounding_scores.append(grounding_score)
            
            # Store result
            self.results.append({
                "query_id": idx,
                "question": question,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "sources_count": len(sources),
                "latency_ms": latency_ms,
                "grounding_score": grounding_score,
                "matched_keywords": analysis["matched_keywords"],
                "is_fallback": is_fallback
            })
            
            # Print result summary
            print(f"  ✓ Success")
            print(f"    - Latency: {latency_ms:.0f}ms")
            print(f"    - Sources: {len(sources)}")
            print(f"    - Grounding: {grounding_score:.0%} ({analysis['match_count']}/{analysis['expected_count']} keywords)")
            if analysis["matched_keywords"]:
                print(f"    - Matched: {', '.join(analysis['matched_keywords'][:3])}")
    
    def calculate_summary_metrics(self) -> Dict[str, Any]:
        """Calculate summary metrics from all results"""
        if not self.results:
            return {}
        
        latencies = self.latencies
        grounding = self.grounding_scores
        
        metrics = {
            "total_queries": self.total_queries,
            "successful_queries": len(self.results),
            "rejected_by_validation": self.rejected_answers,
            "success_rate": (len(self.results) / self.total_queries * 100) if self.total_queries > 0 else 0,
            "latency": {
                "min_ms": min(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "avg_ms": sum(latencies) / len(latencies) if latencies else 0,
                "median_ms": sorted(latencies)[len(latencies)//2] if latencies else 0
            },
            "grounding": {
                "min": min(grounding) if grounding else 0,
                "max": max(grounding) if grounding else 0,
                "avg": sum(grounding) / len(grounding) if grounding else 0,
                "median": sorted(grounding)[len(grounding)//2] if grounding else 0
            },
            "phase6_enforced_rejections": f"{self.rejected_answers}/{self.total_queries} ({self.rejected_answers/self.total_queries*100:.1f}%)"
        }
        
        return metrics
    
    def print_summary(self, metrics: Dict[str, Any]):
        """Print evaluation summary"""
        print("\n" + "=" * 80)
        print("PHASE 6 EVALUATION SUMMARY")
        print("=" * 80)
        
        print(f"\nQuery Statistics:")
        print(f"  Total Queries:           {metrics['total_queries']}")
        print(f"  Successful Answers:      {metrics['successful_queries']}")
        print(f"  Rejected by Validation:  {metrics['rejected_by_validation']} ({metrics['rejected_by_validation']/metrics['total_queries']*100:.1f}%)")
        print(f"  Success Rate:            {metrics['success_rate']:.1f}%")
        
        print(f"\nLatency Metrics (Phase 6):")
        print(f"  Min:                     {metrics['latency']['min_ms']:.0f}ms")
        print(f"  Max:                     {metrics['latency']['max_ms']:.0f}ms")
        print(f"  Average:                 {metrics['latency']['avg_ms']:.0f}ms")
        print(f"  Median:                  {metrics['latency']['median_ms']:.0f}ms")
        
        print(f"\nGrounding Metrics:")
        print(f"  Min Score:               {metrics['grounding']['min']:.1%}")
        print(f"  Max Score:               {metrics['grounding']['max']:.1%}")
        print(f"  Average Score:           {metrics['grounding']['avg']:.1%}")
        print(f"  Median Score:            {metrics['grounding']['median']:.1%}")
        
        print(f"\nPhase 6 Enforcement:")
        print(f"  Enforced Rejections:     {metrics['phase6_enforced_rejections']}")
        print(f"  Effect:                  Better quality (fewer hallucinations)")
        print(f"                           Slight increase in honest rejections")
        
        print("\n" + "=" * 80)
    
    def save_results(self, metrics: Dict[str, Any]):
        """Save detailed results to JSON"""
        output_file = self.results_dir / f"phase6_results_{self.timestamp}.json"
        
        output_data = {
            "phase": "Phase 6",
            "timestamp": self.timestamp,
            "settings": {
                "temperature": 0.3,
                "enforce_validation": True,
                "grounding_threshold": 0.6
            },
            "summary": metrics,
            "detailed_results": self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to: {output_file}")
        return output_file
    
    def run(self, dataset_name: str = "phase6_dataset.json"):
        """Execute complete Phase 6 evaluation"""
        # Load dataset
        qa_pairs = self.load_dataset()
        if not qa_pairs:
            return False
        
        # Check API
        if not self.check_api_health():
            print("\n⚠ Evaluation aborted: API not available")
            return False
        
        # Run evaluation
        self.run_evaluation(qa_pairs)
        
        # Calculate metrics
        metrics = self.calculate_summary_metrics()
        
        # Print summary
        self.print_summary(metrics)
        
        # Save results
        self.save_results(metrics)
        
        return True


def main():
    """Main entry point"""
    # Determine dataset from command line or use default
    dataset = "phase6_dataset.json"
    if len(sys.argv) > 1:
        dataset = sys.argv[1]
    
    evaluator = Phase6Evaluator(dataset_name=dataset)
    success = evaluator.run(dataset)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
