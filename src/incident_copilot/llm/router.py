"""LiteLLM router with ordered provider fallback and simple budget tracking.

Order: Groq (primary) -> Gemini -> OpenRouter. On a rate-limit or provider error
we fall through to the next provider, so a single free-tier cap never stops a run.
Two tiers: 'small' (triage/summaries) and 'large' (hypotheses/report).
"""

from __future__ import annotations

import time
from typing import Any

import litellm

from ..config import get_settings

# Wait out a per-minute rate limit on the SAME model before giving up on it.
# Keeps evals on one model (honest, stable) instead of collapsing to a weak fallback.
_RATE_LIMIT_WAITS = (8.0, 20.0)


class LLMError(RuntimeError):
    pass


class LLMRouter:
    def __init__(self) -> None:
        s = get_settings()
        self.small = [s.groq_model, s.gemini_model, s.openrouter_model]
        self.large = [s.groq_model_large, s.gemini_model, s.openrouter_model]
        self.calls = 0
        self.tokens = 0
        self.last_model = ""

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tier: str = "large",
        timeout: float = 45.0,
    ) -> Any:
        models = self.large if tier == "large" else self.small
        kwargs: dict[str, Any] = {"timeout": timeout, "num_retries": 0}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        last_err: Exception | None = None
        for model in models:
            for attempt in range(len(_RATE_LIMIT_WAITS) + 1):
                try:
                    resp = litellm.completion(model=model, messages=messages, **kwargs)
                except Exception as exc:  # noqa: BLE001 - litellm raises many provider types
                    last_err = exc
                    is_rate = (
                        "ratelimit" in type(exc).__name__.lower()
                        or getattr(exc, "status_code", None) == 429
                    )
                    if is_rate and attempt < len(_RATE_LIMIT_WAITS):
                        time.sleep(_RATE_LIMIT_WAITS[attempt])  # wait out the per-min cap
                        continue
                    break  # not a rate limit (or waits exhausted) — try the next provider
                self.calls += 1
                self.last_model = model
                usage = getattr(resp, "usage", None)
                if usage is not None:
                    self.tokens += getattr(usage, "total_tokens", 0) or 0
                return resp
        raise LLMError(f"all providers failed; last error: {last_err}")
