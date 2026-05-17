#!/usr/bin/env python3
"""
PHASE 4: ANALYSIS & REPORTING
==============================
Analyze Phase 3 results and generate comprehensive report.

Author: AI Engineering Team
Version: 1.0.0
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import numpy as np

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)


class Phase4Analyzer:
    """Analyze Phase 3 results and generate reports"""
    
    def __init__(self):
        self.evaluation_dir = Path(__file__).parent
        self.results_dir = self.evaluation_dir / "results"
        self.config_path = self.evaluation_dir / "evaluation_config.json"
        self.targets = self._load_targets()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _load_targets(self) -> Dict:
        """Load evaluation targets from config"""
        with open(self.config_path, encoding='utf-8') as f:
            config = json.load(f)
        
        targets = {}
        targets.update(config["evaluation_config"]["retrieval_evaluation"]["targets"])
        targets.update(config["evaluation_config"]["generation_evaluation"]["targets"])
        targets.update(config["evaluation_config"]["performance_evaluation"]["targets"])
        
        return targets
    
    def load_latest_results(self) -> tuple:
        """Load latest Phase 3 results"""
        print("\n[STEP 1] Loading Phase 3 Results")
        print("=" * 70)
        
        # Find latest result files
        result_files = sorted(self.results_dir.glob("phase3_results_*.json"))
        agg_files = sorted(self.results_dir.glob("phase3_aggregated_*.json"))
        
        if not result_files or not agg_files:
            print("ERROR: No Phase 3 results found")
            return None, None
        
        latest_result = result_files[-1]
        latest_agg = agg_files[-1]
        
        print(f"Loading: {latest_result.name}")
        print(f"Loading: {latest_agg.name}")
        
        with open(latest_result, encoding='utf-8') as f:
            results = json.load(f)
        
        with open(latest_agg, encoding='utf-8') as f:
            aggregated = json.load(f)
        
        print(f"Total queries evaluated: {len(results['results'])}")
        
        return results, aggregated
    
    def analyze_metrics(self, aggregated: Dict) -> Dict:
        """Analyze metrics against targets"""
        print("\n[STEP 2] Analyzing Metrics Against Targets")
        print("=" * 70)
        
        analysis = {
            "summary": {},
            "retrieval": {},
            "generation": {},
            "performance": {}
        }
        
        # Retrieval analysis
        print("\nRETRIEVAL METRICS:")
        for metric, value in aggregated["retrieval"].items():
            target_key = metric.replace("avg_", "").lower() if "avg_" in metric else metric
            target = self.targets.get(target_key, None)
            
            if target:
                status = "PASS" if value >= target else "FAIL"
                pct = value * 100 if isinstance(value, float) and value <= 1 else value
                print(f"  {metric:.<40} {pct:>6.1f}% (Target: {target*100:.0f}%) [{status}]")
                analysis["retrieval"][metric] = {
                    "value": value,
                    "target": target,
                    "status": status
                }
        
        # Generation analysis
        print("\nGENERATION METRICS:")
        for metric, value in aggregated["generation"].items():
            target_key = metric.replace("avg_", "").lower() if "avg_" in metric else metric
            target = self.targets.get(target_key, None)
            
            if target:
                status = "PASS" if value >= target else "FAIL"
                pct = value * 100 if isinstance(value, float) and value <= 1 else value
                print(f"  {metric:.<40} {pct:>6.1f}% (Target: {target*100:.0f}%) [{status}]")
                analysis["generation"][metric] = {
                    "value": value,
                    "target": target,
                    "status": status
                }
        
        # Performance analysis
        print("\nPERFORMANCE METRICS:")
        for metric, value in aggregated["performance"].items():
            target_key = metric.replace("avg_", "").lower() if "avg_" in metric else metric
            target = self.targets.get(target_key, None)
            
            if target:
                if "latency" in metric or "ms" in metric:
                    status = "PASS" if value <= target else "FAIL"
                    print(f"  {metric:.<40} {value:>8.0f}ms (Target: {target:.0f}ms) [{status}]")
                else:
                    status = "PASS" if value >= target else "FAIL"
                    print(f"  {metric:.<40} {value:>8.2f} (Target: {target:.2f}) [{status}]")
                
                analysis["performance"][metric] = {
                    "value": value,
                    "target": target,
                    "status": status
                }
        
        # Summary
        all_metrics = {**analysis["retrieval"], **analysis["generation"], **analysis["performance"]}
        passed = sum(1 for m in all_metrics.values() if m["status"] == "PASS")
        total = len(all_metrics)
        
        analysis["summary"] = {
            "total_metrics": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0
        }
        
        print(f"\nSUMMARY: {passed}/{total} metrics PASSED ({passed/total*100:.1f}%)")
        
        return analysis
    
    def generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate optimization recommendations"""
        print("\n[STEP 3] Generating Recommendations")
        print("=" * 70)
        
        recommendations = []
        
        # Check retrieval
        for metric, data in analysis["retrieval"].items():
            if data["status"] == "FAIL":
                recommendations.append(f"RETRIEVAL: {metric} is below target ({data['value']:.1%} vs {data['target']:.1%})")
                recommendations.append("  -> Try: Improve embedding model or adjust chunk size")
        
        # Check generation
        for metric, data in analysis["generation"].items():
            if data["status"] == "FAIL":
                if "faithfulness" in metric:
                    recommendations.append(f"GENERATION: Hallucinations detected ({data['value']:.1%})")
                    recommendations.append("  -> Try: Add retrieval validation or stricter prompts")
                elif "relevance" in metric:
                    recommendations.append(f"GENERATION: Relevance is low ({data['value']:.1%})")
                    recommendations.append("  -> Try: Improve LLM prompt or context window")
                elif "completeness" in metric:
                    recommendations.append(f"GENERATION: Answers incomplete ({data['value']:.1%})")
                    recommendations.append("  -> Try: Increase max_tokens or improve prompts")
        
        # Check performance
        for metric, data in analysis["performance"].items():
            if data["status"] == "FAIL":
                if "latency" in metric:
                    recommendations.append(f"PERFORMANCE: Latency too high ({data['value']:.0f}ms vs {data['target']:.0f}ms)")
                    recommendations.append("  -> Try: Optimize Groq API calls or reduce retrieval top-k")
                elif "throughput" in metric:
                    recommendations.append(f"PERFORMANCE: Throughput too low ({data['value']:.2f} q/s vs {data['target']:.2f} q/s)")
                    recommendations.append("  -> Try: Parallelize queries or cache embeddings")
        
        if not recommendations:
            recommendations.append("All metrics are within targets! System is performing well.")
        
        for rec in recommendations:
            print(rec)
        
        return recommendations
    
    def generate_html_report(self, analysis: Dict, aggregated: Dict, recommendations: List[str]) -> str:
        """Generate HTML report"""
        print("\n[STEP 4] Generating HTML Report")
        print("=" * 70)
        
        html = """<!DOCTYPE html>
<html>
<head>
    <title>RAG Evaluation Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }
        .metric-card { background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .metric-label { color: #7f8c8d; font-size: 12px; margin-top: 5px; }
        .pass { color: #27ae60; } .fail { color: #e74c3c; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; background: white; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #34495e; color: white; }
        .recommendations { background: white; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .recommendation { padding: 10px; margin: 5px 0; border-left: 4px solid #3498db; background: #ecf0f1; }
        h1 { color: #2c3e50; } h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>RAG System Evaluation Report</h1>
        <p>Comprehensive analysis of Retrieval-Augmented Generation system performance</p>
    </div>
    
    <div class="metrics">
"""
        
        # Add metric cards
        for metric, data in analysis["retrieval"].items():
            status_class = "pass" if data["status"] == "PASS" else "fail"
            value = f"{data['value']*100:.1f}%"
            html += f"""        <div class="metric-card">
            <div class="metric-value {status_class}">{value}</div>
            <div class="metric-label">{metric}</div>
            <div>Target: {data['target']*100:.1f}%</div>
        </div>
"""
        
        html += """    </div>
    
    <h2>Retrieval Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
"""
        
        for metric, data in analysis["retrieval"].items():
            status_class = "pass" if data["status"] == "PASS" else "fail"
            html += f"""        <tr>
            <td>{metric}</td>
            <td>{data['value']*100:.2f}%</td>
            <td>{data['target']*100:.2f}%</td>
            <td class="{status_class}">{data['status']}</td>
        </tr>
"""
        
        html += """    </table>
    
    <h2>Generation Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
"""
        
        for metric, data in analysis["generation"].items():
            status_class = "pass" if data["status"] == "PASS" else "fail"
            html += f"""        <tr>
            <td>{metric}</td>
            <td>{data['value']*100:.2f}%</td>
            <td>{data['target']*100:.2f}%</td>
            <td class="{status_class}">{data['status']}</td>
        </tr>
"""
        
        html += """    </table>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th><th>Target</th><th>Status</th></tr>
"""
        
        for metric, data in analysis["performance"].items():
            status_class = "pass" if data["status"] == "PASS" else "fail"
            if "latency" in metric:
                value = f"{data['value']:.0f}ms"
                target = f"{data['target']:.0f}ms"
            else:
                value = f"{data['value']:.2f}"
                target = f"{data['target']:.2f}"
            
            html += f"""        <tr>
            <td>{metric}</td>
            <td>{value}</td>
            <td>{target}</td>
            <td class="{status_class}">{data['status']}</td>
        </tr>
"""
        
        html += """    </table>
    
    <h2>Summary</h2>
    <p><strong>Pass Rate:</strong> <span class="pass">""" + f"{analysis['summary']['pass_rate']*100:.1f}%</span> ({analysis['summary']['passed']}/{analysis['summary']['total_metrics']} metrics)</p>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
"""
        
        for rec in recommendations:
            if rec.startswith("  ->"):
                html += f"        <div style='margin-left: 20px; color: #7f8c8d;'>{rec}</div>\n"
            else:
                html += f"        <div class='recommendation'>{rec}</div>\n"
        
        html += """    </div>
</body>
</html>
"""
        
        report_path = self.results_dir / f"evaluation_report_{self.timestamp}.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML Report: {report_path}")
        return str(report_path)
    
    def save_analysis(self, analysis: Dict, recommendations: List[str]):
        """Save analysis to JSON"""
        analysis_file = self.results_dir / f"analysis_{self.timestamp}.json"
        
        data = {
            "timestamp": self.timestamp,
            "analysis": analysis,
            "recommendations": recommendations
        }
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis JSON: {analysis_file}")
    
    def run(self):
        """Execute Phase 4"""
        print("\n" + "="*70)
        print("PHASE 4: ANALYSIS & REPORTING")
        print("="*70)
        
        try:
            # Load results
            results, aggregated = self.load_latest_results()
            if not results:
                return False
            
            # Analyze
            analysis = self.analyze_metrics(aggregated)
            
            # Recommendations
            recommendations = self.generate_recommendations(analysis)
            
            # Generate reports
            html_report = self.generate_html_report(analysis, aggregated, recommendations)
            self.save_analysis(analysis, recommendations)
            
            print("\n" + "="*70)
            print("PHASE 4 COMPLETE")
            print("="*70)
            print(f"\nOpen report in browser: {html_report}")
            
            return True
            
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    analyzer = Phase4Analyzer()
    success = analyzer.run()
    sys.exit(0 if success else 1)
