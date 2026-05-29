#!/usr/bin/env python3
"""
PHASE 6: STANDALONE EVALUATION (NO SERVER REQUIRED)
====================================================
Run RAG system directly with Phase 6 settings without starting FastAPI.
This allows faster evaluation without API startup overhead.

Author: AI Engineering Team
Version: 1.0.0
Date: May 21, 2026
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# Set ADMIN_KEY for config
os.environ['ADMIN_KEY'] = 'test-admin-key'
os.environ['LLM_TEMPERATURE'] = '0.3'
os.environ['ENFORCE_VALIDATION'] = 'true'

from src.rag_chain import rag_chain
from src.config import config


class Phase6StandaloneEvaluator:
    """Direct Phase 6 Evaluation without FastAPI"""
    
    def __init__(self, dataset_name: str = "phase6_dataset.json"):
        self.evaluation_dir = Path(__file__).parent
        self.dataset_path = self.evaluation_dir / dataset_name
        self.results_dir = self.evaluation_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = []
        self.latencies = []
        self.grounding_scores = []
        self.rejected_answers = 0
        self.total_queries = 0
        self.errors = 0
        
    def load_dataset(self) -> List[Dict]:
        """Load Phase 6 evaluation dataset"""
        print("\n" + "=" * 80)
        print("PHASE 6: STANDALONE EVALUATION (NO SERVER)")
        print("=" * 80)
        print("\n[STEP 1] Loading Phase 6 Evaluation Dataset")
        print("-" * 80)
        
        if not self.dataset_path.exists():
            print(f"ERROR: Dataset not found at {self.dataset_path}")
            return []
            
        try:
            with open(self.dataset_path, encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                qa_pairs = data
            else:
                qa_pairs = data.get("qa_pairs", data)
            
            print(f"✓ Loaded {len(qa_pairs)} test questions")
            print(f"  Dataset: {self.dataset_path.name}")
            return qa_pairs
        except Exception as e:
            print(f"ERROR loading dataset: {e}")
            return []
    
    def verify_configuration(self):
        """Verify Phase 6 configuration is active"""
        print("\n[STEP 2] Verifying Phase 6 Configuration")
        print("-" * 80)
        
        print(f"✓ Configuration Loaded:")
        print(f"  - LLM Temperature: {config.LLM_TEMPERATURE} (Phase 6: should be 0.3)")
        print(f"  - Enforce Validation: {config.ENFORCE_VALIDATION} (Phase 6: should be True)")
        print(f"  - Grounding Threshold: {config.GROUNDING_THRESHOLD} (Phase 6: should be 0.6)")
        print(f"  - Max Tokens: {config.LLM_MAX_TOKENS}")
        print(f"  - Retrieval Top-K: {config.RETRIEVAL_TOP_K}")
        
        # Validate Phase 6 settings
        checks_passed = 0
        checks_total = 3
        
        if config.LLM_TEMPERATURE == 0.3:
            checks_passed += 1
            print(f"  ✓ Temperature is correct (0.3)")
        else:
            print(f"  ✗ Temperature mismatch: {config.LLM_TEMPERATURE} != 0.3")
        
        if config.ENFORCE_VALIDATION:
            checks_passed += 1
            print(f"  ✓ Validation enforcement enabled")
        else:
            print(f"  ✗ Validation enforcement NOT enabled")
        
        if config.GROUNDING_THRESHOLD == 0.6:
            checks_passed += 1
            print(f"  ✓ Grounding threshold correct (0.6)")
        else:
            print(f"  ✗ Grounding threshold mismatch: {config.GROUNDING_THRESHOLD} != 0.6")
        
        print(f"\n  Configuration Check: {checks_passed}/{checks_total} passed")
        return checks_passed == checks_total
    
    def analyze_answer_grounding(self, answer: str, expected_patterns: List[str]) -> Dict[str, any]:
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
            "has_answer": len(answer) > 10,
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
            safe_question = question[:60] if len(question) > 60 else question
            print(f"\n[{idx:2d}/{total}] {safe_question}")
            
            try:
                # Query RAG system directly
                start_time = time.time()
                result = rag_chain.query(question, user_id="phase6_eval")
                latency_ms = (time.time() - start_time) * 1000
                
                self.latencies.append(latency_ms)
                
                answer = result.get("answer", "")
                sources = result.get("sources", [])
                
                # Check if answer is a fallback (Phase 6 rejection)
                is_fallback = "don't have enough information" in answer or "cannot confidently" in answer.lower()
                
                if is_fallback:
                    self.rejected_answers += 1
                    print(f"  ⚠ Answer REJECTED by Phase 6 validation")
                    print(f"    └─ Grounding too low (below {config.GROUNDING_THRESHOLD:.0%} threshold)")
                    print(f"    └─ Latency: {latency_ms:.0f}ms")
                    continue
                
                # Analyze grounding
                analysis = self.analyze_answer_grounding(answer, expected_patterns)
                grounding_score = analysis["grounding_score"]
                self.grounding_scores.append(grounding_score)
                
                # Store result
                self.results.append({
                    "query_id": idx,
                    "question": question,
                    "answer": answer[:150] + "..." if len(answer) > 150 else answer,
                    "sources_count": len(sources),
                    "latency_ms": latency_ms,
                    "grounding_score": grounding_score,
                    "matched_keywords": analysis["matched_keywords"],
                    "is_fallback": is_fallback
                })
                
                # Print result summary
                print(f"  ✓ Success")
                print(f"    ├─ Latency: {latency_ms:.0f}ms")
                print(f"    ├─ Sources: {len(sources)}")
                print(f"    └─ Grounding: {grounding_score:.0%} ({analysis['match_count']}/{analysis['expected_count']} keywords)")
                
                if analysis["matched_keywords"]:
                    keywords_str = ", ".join(analysis["matched_keywords"][:3])
                    if len(analysis["matched_keywords"]) > 3:
                        keywords_str += f", +{len(analysis['matched_keywords']) - 3}"
                    print(f"       Matched: {keywords_str}")
                    
            except Exception as e:
                self.errors += 1
                print(f"  ✗ Query failed: {str(e)[:80]}")
                self.latencies.append(0)
    
    def calculate_summary_metrics(self) -> Dict[str, any]:
        """Calculate summary metrics"""
        if not self.results:
            return {}
        
        latencies = [l for l in self.latencies if l > 0]
        grounding = self.grounding_scores
        
        metrics = {
            "total_queries": self.total_queries,
            "successful_queries": len(self.results),
            "rejected_by_validation": self.rejected_answers,
            "query_errors": self.errors,
            "success_rate": (len(self.results) / self.total_queries * 100) if self.total_queries > 0 else 0,
            "latency": {
                "min_ms": min(latencies) if latencies else 0,
                "max_ms": max(latencies) if latencies else 0,
                "avg_ms": sum(latencies) / len(latencies) if latencies else 0,
                "median_ms": sorted(latencies)[len(latencies)//2] if latencies else 0,
                "total_queries_timed": len(latencies)
            },
            "grounding": {
                "min": min(grounding) if grounding else 0,
                "max": max(grounding) if grounding else 0,
                "avg": sum(grounding) / len(grounding) if grounding else 0,
                "median": sorted(grounding)[len(grounding)//2] if grounding else 0,
                "high_confidence": sum(1 for g in grounding if g >= 0.7),
                "medium_confidence": sum(1 for g in grounding if 0.4 <= g < 0.7),
                "low_confidence": sum(1 for g in grounding if g < 0.4)
            }
        }
        
        return metrics
    
    def print_summary(self, metrics: Dict[str, any]):
        """Print evaluation summary"""
        print("\n" + "=" * 80)
        print("PHASE 6 EVALUATION RESULTS")
        print("=" * 80)
        
        print(f"\nQuery Statistics:")
        print(f"  Total Queries:           {metrics['total_queries']}")
        print(f"  Successful Answers:      {metrics['successful_queries']}")
        print(f"  Rejected by Validation:  {metrics['rejected_by_validation']} ({metrics['rejected_by_validation']/metrics['total_queries']*100:.1f}%)")
        print(f"  Query Errors:            {metrics['query_errors']}")
        print(f"  Success Rate:            {metrics['success_rate']:.1f}%")
        
        print(f"\nLatency Performance (Phase 6):")
        print(f"  Min Latency:             {metrics['latency']['min_ms']:.0f}ms")
        print(f"  Max Latency:             {metrics['latency']['max_ms']:.0f}ms")
        print(f"  Average Latency:         {metrics['latency']['avg_ms']:.0f}ms")
        print(f"  Median Latency:          {metrics['latency']['median_ms']:.0f}ms")
        
        print(f"\nGrounding Metrics:")
        print(f"  Min Grounding Score:     {metrics['grounding']['min']:.1%}")
        print(f"  Max Grounding Score:     {metrics['grounding']['max']:.1%}")
        print(f"  Average Grounding:       {metrics['grounding']['avg']:.1%}")
        print(f"  Median Grounding:        {metrics['grounding']['median']:.1%}")
        
        print(f"\nConfidence Distribution:")
        print(f"  High Confidence (≥70%):  {metrics['grounding']['high_confidence']} queries")
        print(f"  Medium Confidence (40-70%): {metrics['grounding']['medium_confidence']} queries")
        print(f"  Low Confidence (<40%):   {metrics['grounding']['low_confidence']} queries")
        
        print(f"\nPhase 6 Enforcement:")
        print(f"  Enforced Rejections:     {metrics['rejected_by_validation']}/{metrics['total_queries']} ({metrics['rejected_by_validation']/metrics['total_queries']*100:.1f}%)")
        print(f"  Effect:                  Fewer hallucinations")
        print(f"                           More honest responses")
        print(f"                           Better user trust")
        
        print("\n" + "=" * 80)
    
    def save_results(self, metrics: Dict[str, any]):
        """Save detailed results to JSON"""
        output_file = self.results_dir / f"phase6_results_{self.timestamp}.json"
        
        output_data = {
            "phase": "Phase 6",
            "evaluation_type": "Standalone (Direct RAG Chain)",
            "timestamp": self.timestamp,
            "settings": {
                "temperature": config.LLM_TEMPERATURE,
                "enforce_validation": config.ENFORCE_VALIDATION,
                "grounding_threshold": config.GROUNDING_THRESHOLD,
                "max_tokens": config.LLM_MAX_TOKENS
            },
            "summary": metrics,
            "detailed_results": self.results[:10]  # Save first 10 for brevity
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
        
        # Verify configuration
        if not self.verify_configuration():
            print("\n⚠ Warning: Some Phase 6 settings may not be optimal")
        
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
    dataset = "phase6_dataset.json"
    if len(sys.argv) > 1:
        dataset = sys.argv[1]
    
    evaluator = Phase6StandaloneEvaluator(dataset_name=dataset)
    success = evaluator.run(dataset)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
