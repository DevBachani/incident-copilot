"""Objective scoring of a report against a scenario's ground truth, plus stats helpers."""

from __future__ import annotations

import math
from typing import Any


def _match(service: str, category: str, expected: dict[str, Any]) -> bool:
    return service == expected["root_cause_service"] and category == expected["root_cause_category"]


def score_report(report: dict[str, Any], expected: dict[str, Any]) -> dict[str, bool]:
    """top-1 (rank-1 correct), top-3 (correct in first 3 hypotheses), action correctness."""
    top1 = _match(report["root_cause_service"], report["root_cause_category"], expected)
    hyps = sorted(report.get("hypotheses", []), key=lambda h: h.get("rank", 99))[:3]
    top3 = top1 or any(
        _match(h["root_cause_service"], h["root_cause_category"], expected) for h in hyps
    )
    action_text = report.get("recommended_action", "").lower()
    action_ok = any(
        a in action_text or a.replace("_", " ") in action_text
        for a in expected.get("acceptable_actions", [])
    )
    return {"top1": top1, "top3": top3, "action": action_ok}


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    """Return (point, lo, hi) — the Wilson 95% CI for a proportion."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(p, 3), round(max(0.0, center - margin), 3), round(min(1.0, center + margin), 3))
