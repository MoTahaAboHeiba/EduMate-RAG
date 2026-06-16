#!/usr/bin/env python3
"""Generation evaluation: API capture + offline NLI (+ optional Groq judge)."""
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from evaluation.metrics.groq_judge import GroqJudge
from evaluation.metrics.nli_evaluator import NLIEvaluator

STOPWORDS = {
    "about", "after", "also", "and", "are", "been", "being", "between", "can",
    "could", "does", "for", "from", "has", "have", "into", "less", "more", "must",
    "not", "only", "such", "than", "that", "the", "their", "there", "these",
    "this", "those", "through", "were", "what", "when", "where", "which", "while",
    "with", "would", "your", "lines", "input", "output",
}


def extract_expected_concepts(answer: str, limit: int = 6) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", answer or "")
    seen = set()
    concepts = []
    for token in tokens:
        low = token.lower()
        if low in STOPWORDS or low in seen:
            continue
        seen.add(low)
        concepts.append(token)
        if len(concepts) >= limit:
            break
    return concepts


def load_phase6_patterns() -> Dict[str, List[str]]:
    path = project_root / "evaluation" / "phase6_dataset.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)
    return {row["question"].strip().lower(): row["expected_answer_pattern"] for row in rows}


def build_subset(dataset_path: Path, retrieval_path: Path, out_path: Path, target: int = 28) -> Dict:
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)
    with open(retrieval_path, encoding="utf-8") as f:
        retrieval = json.load(f)

    experiment = next(
        e for e in retrieval["experiments"]
        if e["config"]["threshold"] == 0.0 and e["config"]["top_k"] == 5
    )
    by_id = {qa["id"]: qa for qa in dataset["qa_pairs"]}
    phase6 = load_phase6_patterns()

    buckets = {"easy": [], "medium": [], "hard": []}
    for row in experiment["per_query"]:
        qid = row["question_id"]
        qa = by_id.get(qid)
        if not qa:
            continue
        hr5 = row["metrics"]["hit_rate_at_5"]
        mrr = row["metrics"]["mrr"]
        if hr5 >= 1.0 and mrr >= 1.0:
            bucket = "easy"
        elif hr5 <= 0.0 or mrr <= 0.0:
            bucket = "hard"
        else:
            bucket = "medium"
        buckets[bucket].append((qid, qa, row))

    targets = {"easy": 10, "medium": 10, "hard": 8}
    selected = []
    used_categories = defaultdict(int)

    for bucket, count in targets.items():
        pool = sorted(
            buckets[bucket],
            key=lambda item: (used_categories[item[1].get("category", "")], item[0]),
        )
        for qid, qa, row in pool:
            if sum(1 for s in selected if s["stratum"] == bucket) >= count:
                break
            concepts = phase6.get(qa["question"].strip().lower()) or extract_expected_concepts(qa.get("answer", ""))
            selected.append({
                "id": qid,
                "question": qa["question"],
                "answer": qa.get("answer", ""),
                "category": qa.get("category", "unknown"),
                "ground_truth_docs": qa["ground_truth_docs"],
                "expected_concepts": concepts,
                "stratum": bucket,
                "retrieval_baseline": {
                    "hit_rate_at_5": row["metrics"]["hit_rate_at_5"],
                    "mrr": row["metrics"]["mrr"],
                    "precision_at_5": row["metrics"]["precision_at_5"],
                },
            })
            used_categories[qa.get("category", "unknown")] += 1

    payload = {
        "metadata": {
            "name": "EduMate Generation Eval Subset v1",
            "version": "1.0.0",
            "total_questions": len(selected),
            "strata": targets,
            "source_retrieval_baseline": retrieval_path.name,
        },
        "qa_pairs": selected[:target],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


class GenerationEvaluator:
    def __init__(self):
        self.eval_dir = Path(__file__).parent
        self.results_dir = self.eval_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.subset_path = self.eval_dir / "datasets" / "generation_eval_subset_v1.json"
        self.dataset_path = self.eval_dir / "datasets" / "rag_evaluation_dataset_v1.json"
        self.retrieval_path = self.eval_dir / "results" / "retrieval_eval_20260612_160420.json"
        self.api_base = os.getenv("EDUMATE_EVAL_API_BASE_URL", "http://localhost:8000").rstrip("/")
        self.top_k = int(os.getenv("GEN_EVAL_TOP_K", "5"))
        self.sleep_s = float(os.getenv("GEN_EVAL_SLEEP", "2"))
        self.use_groq_judge = os.getenv("GEN_EVAL_USE_GROQ_JUDGE", "true").lower() in {"1", "true", "yes"}
        self.start = int(os.getenv("GEN_EVAL_START", "0"))
        self.limit = int(os.getenv("GEN_EVAL_LIMIT", "0")) or None
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.nli = NLIEvaluator()
        self.judge = GroqJudge() if self.use_groq_judge else None

    def load_subset(self) -> List[Dict]:
        if not self.subset_path.exists():
            print(f"Building subset -> {self.subset_path.name}")
            build_subset(self.dataset_path, self.retrieval_path, self.subset_path)
        with open(self.subset_path, encoding="utf-8") as f:
            data = json.load(f)
        pairs = data["qa_pairs"][self.start:]
        if self.limit:
            pairs = pairs[: self.limit]
        return pairs

    def check_api(self) -> bool:
        try:
            resp = requests.get(f"{self.api_base}/health", timeout=8)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def capture_query(self, qa: Dict, session_token: str) -> Dict:
        headers = {
            "X-Session-Token": session_token,
            "X-Evaluation-Mode": "true",
        }
        for attempt in range(5):
            try:
                resp = requests.post(
                    f"{self.api_base}/api/query",
                    json={"question": qa["question"], "num_context_docs": self.top_k},
                    headers=headers,
                    timeout=int(os.getenv("EDUMATE_EVAL_QUERY_TIMEOUT", "90")),
                )
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 503 and attempt < 4:
                    time.sleep(15 * (attempt + 1))
                    continue
                resp.raise_for_status()
            except requests.RequestException as exc:
                if attempt < 4:
                    time.sleep(10 * (attempt + 1))
                    continue
                raise exc
        raise RuntimeError("capture_failed")

    def capture(self, qa_pairs: List[Dict]) -> List[Dict]:
        captures = []
        prefix = f"gen-eval-{self.timestamp}"
        for idx, qa in enumerate(qa_pairs, 1):
            print(f"[{idx}/{len(qa_pairs)}] capture {qa['id']}...", end=" ", flush=True)
            t0 = time.perf_counter()
            result = self.capture_query(qa, f"{prefix}-{qa['id']}")
            latency_ms = (time.perf_counter() - t0) * 1000
            captures.append({
                "question_id": qa["id"],
                "question": qa["question"],
                "category": qa.get("category"),
                "stratum": qa.get("stratum"),
                "ground_truth_docs": qa["ground_truth_docs"],
                "expected_concepts": qa.get("expected_concepts", []),
                "retrieval_baseline": qa.get("retrieval_baseline", {}),
                "generated_answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "context_chunks": result.get("context_chunks", []),
                "is_general": result.get("is_general", False),
                "latency_ms": latency_ms,
                "timings_ms": result.get("timings_ms", {}),
            })
            print(f"OK ({latency_ms:.0f}ms)")
            if idx < len(qa_pairs):
                time.sleep(self.sleep_s)
        return captures

    def score_capture(self, capture: Dict) -> Dict:
        answer = capture["generated_answer"]
        chunks = capture["context_chunks"]
        faith = self.nli.score_faithfulness(answer, chunks)
        metrics = {
            "mcf": faith["mcf"],
            "nli_relevance": self.nli.score_relevance(capture["question"], answer),
            "concept_coverage": self.nli.score_concept_coverage(answer, capture.get("expected_concepts", [])),
            "source_accuracy": self.nli.score_source_accuracy(capture.get("sources", []), capture["ground_truth_docs"]),
            "num_claims": faith["num_claims"],
        }
        if self.judge:
            judged = self.judge.score(
                capture["question"],
                answer,
                chunks,
                capture.get("expected_concepts", []),
            )
            metrics["groq_relevance"] = judged["relevance"]
            metrics["groq_completeness"] = judged["completeness"]
            metrics["groq_reason"] = judged["reason"]
            time.sleep(self.sleep_s)
        return metrics

    def aggregate(self, rows: List[Dict]) -> Dict:
        def mean(key: str) -> float:
            vals = [r["metrics"][key] for r in rows if key in r["metrics"]]
            return float(np.mean(vals)) if vals else 0.0

        def by_stratum(name: str) -> Dict:
            subset = [r for r in rows if r.get("stratum") == name]
            return {
                "n": len(subset),
                "mcf": float(np.mean([r["metrics"]["mcf"] for r in subset])) if subset else 0.0,
            }

        mcf_vals = [r["metrics"]["mcf"] for r in rows]
        ci = float(np.std(mcf_vals) / np.sqrt(len(mcf_vals))) if len(mcf_vals) > 1 else 0.0
        latencies = [r["latency_ms"] for r in rows]

        report = {
            "timestamp": self.timestamp,
            "evaluation_version": "generation_v1",
            "num_queries": len(rows),
            "headline_metric": {
                "name": "Mean Context Faithfulness (MCF)",
                "value": mean("mcf"),
                "std_error": ci,
            },
            "supporting_metrics": {
                "avg_source_accuracy": mean("source_accuracy"),
                "avg_nli_relevance": mean("nli_relevance"),
                "avg_concept_coverage": mean("concept_coverage"),
                "avg_groq_relevance": mean("groq_relevance"),
                "avg_groq_completeness": mean("groq_completeness"),
                "median_latency_ms": float(np.median(latencies)) if latencies else 0.0,
                "p95_latency_ms": float(np.percentile(latencies, 95)) if latencies else 0.0,
            },
            "stratified": {
                "easy": by_stratum("easy"),
                "medium": by_stratum("medium"),
                "hard": by_stratum("hard"),
            },
            "groq_judge_model": os.getenv("GROQ_JUDGE_MODEL", "llama-3.3-70b-versatile") if self.use_groq_judge else None,
            "per_query": rows,
        }
        failures = [r for r in rows if r["metrics"]["mcf"] < 0.5]
        report["failure_analysis"] = [
            {
                "question_id": r["question_id"],
                "question": r["question"][:160],
                "mcf": r["metrics"]["mcf"],
                "retrieval_hit_rate_at_5": r.get("retrieval_baseline", {}).get("hit_rate_at_5"),
                "root_cause": (
                    "retrieval_miss" if r.get("retrieval_baseline", {}).get("hit_rate_at_5", 1) == 0
                    else "generation_issue"
                ),
            }
            for r in sorted(failures, key=lambda x: x["metrics"]["mcf"])[:10]
        ]
        return report

    def run(self):
        qa_pairs = self.load_subset()
        if not self.check_api():
            print("ERROR: API not reachable. Start server: python run_dev.py")
            sys.exit(1)

        print(f"Capturing {len(qa_pairs)} queries via API (top_k={self.top_k})...")
        captures = self.capture(qa_pairs)

        capture_file = self.results_dir / f"generation_capture_{self.timestamp}.json"
        with open(capture_file, "w", encoding="utf-8") as f:
            json.dump({"timestamp": self.timestamp, "captures": captures}, f, indent=2)

        print("Scoring offline (NLI" + (" + Groq judge" if self.judge else "") + ")...")
        scored = []
        for idx, cap in enumerate(captures, 1):
            print(f"[{idx}/{len(captures)}] score {cap['question_id']}...", end=" ", flush=True)
            metrics = self.score_capture(cap)
            scored.append({**cap, "metrics": metrics})
            print(f"MCF={metrics['mcf']:.3f}")

        report = self.aggregate(scored)
        report_file = self.results_dir / f"generation_eval_{self.timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        mcf = report["headline_metric"]["value"]
        print("\n=== Generation Evaluation Summary ===")
        print(f"MCF (headline):          {mcf:.4f}")
        print(f"Source accuracy:         {report['supporting_metrics']['avg_source_accuracy']:.4f}")
        print(f"NLI relevance:           {report['supporting_metrics']['avg_nli_relevance']:.4f}")
        if self.judge:
            print(f"Groq relevance:          {report['supporting_metrics']['avg_groq_relevance']:.4f}")
            print(f"Groq completeness:       {report['supporting_metrics']['avg_groq_completeness']:.4f}")
        print(f"Median latency (ms):     {report['supporting_metrics']['median_latency_ms']:.0f}")
        print(f"Capture file:            {capture_file.name}")
        print(f"Report file:             {report_file.name}")


if __name__ == "__main__":
    GenerationEvaluator().run()
