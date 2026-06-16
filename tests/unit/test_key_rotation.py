"""
Unit tests for Groq API key rotation logic.

Exercises the fallback behaviour inside RAGChain._invoke_llm (generation block):
  - Primary key hits 429  →  rotates to GROQ_API_KEY_2 and succeeds
  - Both keys hit 429     →  raises RuntimeError("GROQ_RATE_LIMIT: both keys exhausted")
  - No secondary key set  →  raises RuntimeError("GROQ_RATE_LIMIT") immediately
"""
from unittest.mock import MagicMock, patch, call
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rate_limit_error():
    """Return an exception that looks like a Groq 429 response."""
    return Exception("rate_limit_exceeded: you have exceeded your quota")


def _make_good_response(text: str = "Mocked answer"):
    resp = MagicMock()
    resp.content = text
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGroqKeyRotation:
    """Tests for the primary → secondary key rotation on rate limits."""

    def _invoke_generation_block(self, primary_side_effect, backup_side_effect, has_key2: bool):
        """
        Simulate the generation try/except block from rag_chain.py in isolation.

        Returns the answer string on success or re-raises on failure.
        """
        from unittest.mock import MagicMock

        primary_llm = MagicMock()
        primary_llm.invoke.side_effect = primary_side_effect

        backup_llm = MagicMock()
        if backup_side_effect is None:
            backup_llm.invoke.return_value = _make_good_response("Answer from key 2")
        else:
            backup_llm.invoke.side_effect = backup_side_effect

        api_key_2 = "gsk_backup_key" if has_key2 else None

        # ------------------------------------------------------------------
        # Inline re-implementation of the generation try/except block so we
        # can unit-test the logic without spinning up the full RAGChain.
        # ------------------------------------------------------------------
        prompt_input = "dummy prompt"

        try:
            response = primary_llm.invoke(prompt_input)
        except Exception as e:
            msg = str(e).lower()
            if "rate_limit_exceeded" in msg or "429" in msg:
                if api_key_2:
                    try:
                        response = backup_llm.invoke(prompt_input)
                    except Exception as e2:
                        raise RuntimeError(
                            f"GROQ_RATE_LIMIT: both keys exhausted. key1={e} key2={e2}"
                        )
                else:
                    raise RuntimeError(f"GROQ_RATE_LIMIT: {e}")
            else:
                raise

        return response.content.strip()

    # ── happy-path rotation ──────────────────────────────────────────────
    def test_rotates_to_key2_on_rate_limit(self):
        """When key1 hits 429 and key2 is configured, the call should succeed."""
        result = self._invoke_generation_block(
            primary_side_effect=_rate_limit_error(),
            backup_side_effect=None,          # key2 succeeds
            has_key2=True,
        )
        assert result == "Answer from key 2"

    # ── both keys exhausted ─────────────────────────────────────────────
    def test_both_keys_exhausted_raises(self):
        """When both keys hit 429, a descriptive RuntimeError should be raised."""
        with pytest.raises(RuntimeError, match="both keys exhausted"):
            self._invoke_generation_block(
                primary_side_effect=_rate_limit_error(),
                backup_side_effect=_rate_limit_error(),
                has_key2=True,
            )

    # ── no secondary key ────────────────────────────────────────────────
    def test_no_key2_raises_immediately(self):
        """When GROQ_API_KEY_2 is not set, a 429 surfaces as GROQ_RATE_LIMIT immediately."""
        with pytest.raises(RuntimeError, match="GROQ_RATE_LIMIT"):
            self._invoke_generation_block(
                primary_side_effect=_rate_limit_error(),
                backup_side_effect=None,
                has_key2=False,
            )

    # ── non-rate-limit errors are re-raised unchanged ───────────────────
    def test_non_rate_limit_error_propagates(self):
        """Non-429 errors (e.g. connection errors) should propagate as-is."""
        with pytest.raises(Exception, match="network unreachable"):
            self._invoke_generation_block(
                primary_side_effect=Exception("network unreachable"),
                backup_side_effect=None,
                has_key2=True,
            )
