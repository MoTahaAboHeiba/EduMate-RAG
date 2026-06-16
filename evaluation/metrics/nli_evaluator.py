"""Local faithfulness metrics using project ONNX embeddings (no Groq, no PyTorch)."""
import re
from typing import Dict, List

import numpy as np
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

CLAIM_MIN_LEN = 12
CHUNK_CHAR_LIMIT = 1800


class NLIEvaluator:
    """Semantic entailment proxy via cosine similarity on MiniLM embeddings."""

    def __init__(self):
        self.embed_fn = DefaultEmbeddingFunction()

    @staticmethod
    def is_conversational_claim(claim: str) -> bool:
        c_low = claim.strip().lower()
        c_clean = re.sub(r"^[^\w\s]+", "", c_low)
        patterns = [
            r"^that's correct",
            r"^correct\b",
            r"^according to",
            r"^based on",
            r"^as stated",
            r"^as mentioned",
            r"^sure\b",
            r"^yes\b",
            r"^indeed\b",
            r"^in the section on",
            r"^this is specified in",
            r"^this is stated in",
            r"^the section on",
            r"^according to table",
        ]
        return any(re.search(pat, c_clean) for pat in patterns)

    @staticmethod
    def split_claims(answer: str) -> List[str]:
        if not answer or not answer.strip():
            return []
        parts = re.split(r"(?<=[.!?])\s+|\n+", answer.strip())
        claims = []
        for p in parts:
            p_strip = p.strip()
            if len(p_strip) < CLAIM_MIN_LEN:
                continue
            if NLIEvaluator.is_conversational_claim(p_strip):
                continue
            claims.append(p_strip)
        return claims or [answer.strip()]

    @staticmethod
    def _truncate(text: str, limit: int = CHUNK_CHAR_LIMIT) -> str:
        text = (text or "").strip()
        return text if len(text) <= limit else text[:limit]

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        va = np.asarray(a, dtype=np.float32)
        vb = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
        if denom == 0.0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        return self.embed_fn([self._truncate(t) for t in texts if t.strip()])

    def score_faithfulness(self, answer: str, context_chunks: List[Dict]) -> Dict:
        claims = self.split_claims(answer)
        if not claims:
            return {"mcf": 0.0, "claim_scores": [], "num_claims": 0}
        if not context_chunks:
            return {"mcf": 0.0, "claim_scores": [0.0] * len(claims), "num_claims": len(claims)}

        claim_embs = self._embed(claims)
        chunk_texts = [c.get("content", "") for c in context_chunks if c.get("content", "").strip()]
        chunk_embs = self._embed(chunk_texts)
        if not chunk_embs:
            return {"mcf": 0.0, "claim_scores": [0.0] * len(claims), "num_claims": len(claims)}

        claim_scores = [max(self._cosine(ce, che) for che in chunk_embs) for ce in claim_embs]
        return {
            "mcf": sum(claim_scores) / len(claim_scores),
            "claim_scores": claim_scores,
            "num_claims": len(claims),
        }

    def score_relevance(self, question: str, answer: str) -> float:
        if not question.strip() or not answer.strip():
            return 0.0
        q_emb, a_emb = self._embed([question, answer])
        return max(0.0, self._cosine(q_emb, a_emb))

    @staticmethod
    def score_concept_coverage(answer: str, expected_concepts: List[str]) -> float:
        if not expected_concepts:
            return 0.0
        answer_l = answer.lower()
        hits = sum(1 for term in expected_concepts if term.lower() in answer_l)
        return hits / len(expected_concepts)

    @staticmethod
    def score_source_accuracy(retrieved_sources: List[str], ground_truth_docs: List[str]) -> float:
        if not ground_truth_docs:
            return 0.0
        gt = {doc.strip().lower() for doc in ground_truth_docs}
        retrieved = {src.strip().lower() for src in retrieved_sources}
        return 1.0 if retrieved & gt else 0.0
