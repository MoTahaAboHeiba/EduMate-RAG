"""Groq LLM judge via native SDK (avoids langchain/torch import chain)."""
import json
import os
import re
import time
from typing import Dict, List, Optional

from groq import Groq

JUDGE_PROMPT = """You are an expert RAG evaluator. Score the answer using ONLY the provided context.

Question: {question}
Expected concepts: {concepts}
Context excerpt:
{context}

Generated answer:
{answer}

Return ONLY valid JSON:
{{"relevance": <0.0-1.0>, "completeness": <0.0-1.0>, "reason": "<one sentence>"}}
"""


class GroqJudge:
    def __init__(
        self,
        model: Optional[str] = None,
        primary_key: Optional[str] = None,
        fallback_key: Optional[str] = None,
    ):
        self.model = model or os.getenv("GROQ_JUDGE_MODEL", "llama-3.3-70b-versatile")
        self.primary_key = primary_key or os.getenv("GROQ_API_KEY", "")
        self.fallback_key = fallback_key or os.getenv("GROQ_API_KEY_2", "")
        self.clients = [Groq(api_key=self.primary_key)]
        if self.fallback_key:
            self.clients.append(Groq(api_key=self.fallback_key))

    @staticmethod
    def _context_excerpt(chunks: List[Dict], limit: int = 2500) -> str:
        parts, total = [], 0
        for chunk in chunks:
            text = (chunk.get("content") or "").strip()
            if not text:
                continue
            piece = f"[{chunk.get('source', 'unknown')}] {text}"
            if total + len(piece) > limit:
                piece = piece[: max(0, limit - total)]
            parts.append(piece)
            total += len(piece)
            if total >= limit:
                break
        return "\n\n".join(parts) or "(no context)"

    @staticmethod
    def _parse_json(text: str) -> Dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {"relevance": 0.0, "completeness": 0.0, "reason": "parse_error"}
        try:
            data = json.loads(match.group(0))
            return {
                "relevance": float(max(0.0, min(1.0, data.get("relevance", 0.0)))),
                "completeness": float(max(0.0, min(1.0, data.get("completeness", 0.0)))),
                "reason": str(data.get("reason", ""))[:240],
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"relevance": 0.0, "completeness": 0.0, "reason": "parse_error"}

    def _invoke(self, prompt: str) -> str:
        for attempt in range(6):
            client = self.clients[min(attempt // 2, len(self.clients) - 1)]
            try:
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256,
                )
                return resp.choices[0].message.content or ""
            except Exception as exc:
                msg = str(exc).lower()
                if "rate" in msg or "429" in msg or "503" in msg:
                    time.sleep(12 * (attempt + 1))
                    continue
                raise
        raise RuntimeError("GROQ_JUDGE_RATE_LIMIT")

    def score(
        self,
        question: str,
        answer: str,
        context_chunks: List[Dict],
        expected_concepts: List[str],
    ) -> Dict:
        prompt = JUDGE_PROMPT.format(
            question=question,
            concepts=", ".join(expected_concepts) if expected_concepts else "(none)",
            context=self._context_excerpt(context_chunks),
            answer=answer,
        )
        return self._parse_json(self._invoke(prompt))
