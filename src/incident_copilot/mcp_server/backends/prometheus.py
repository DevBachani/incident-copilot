"""Thin Prometheus HTTP API client + metric summarisation helpers.

Tools never return raw time series — only compact summaries, to respect the
free-tier token budget.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ...config import get_settings
from ..schemas import SeriesSummary, Trend


class PrometheusClient:
    def __init__(self, base_url: str | None = None, timeout: float = 15.0) -> None:
        self.base = (base_url or get_settings().prometheus_url).rstrip("/")
        self.timeout = timeout

    def _instant(self, expr: str) -> list[dict[str, Any]]:
        resp = httpx.get(f"{self.base}/api/v1/query", params={"query": expr}, timeout=self.timeout)
        resp.raise_for_status()
        result: list[dict[str, Any]] = resp.json()["data"]["result"]
        return result

    def scalar(self, expr: str) -> float | None:
        """First value of an instant query, or None if empty/NaN."""
        result = self._instant(expr)
        if not result:
            return None
        try:
            value = float(result[0]["value"][1])
        except (ValueError, KeyError, IndexError):
            return None
        return None if value != value else value  # drop NaN

    def range_summaries(
        self, expr: str, minutes: int = 15, step: str = "30s", max_series: int = 8
    ) -> tuple[list[SeriesSummary], bool]:
        end = time.time()
        start = end - minutes * 60
        resp = httpx.get(
            f"{self.base}/api/v1/query_range",
            params={"query": expr, "start": start, "end": end, "step": step},
            timeout=self.timeout + 10,
        )
        resp.raise_for_status()
        results = resp.json()["data"]["result"]
        truncated = len(results) > max_series
        summaries: list[SeriesSummary] = []
        for item in results[:max_series]:
            values = [float(v[1]) for v in item["values"] if v[1] not in ("NaN", "+Inf", "-Inf")]
            if not values:
                continue
            summaries.append(
                SeriesSummary(
                    labels=_fmt_labels(item.get("metric", {})),
                    min=round(min(values), 4),
                    max=round(max(values), 4),
                    latest=round(values[-1], 4),
                    trend=_trend(values),
                )
            )
        return summaries, truncated

    def list_services(self) -> list[str]:
        result = self._instant("count by (service)(shop_http_requests_total)")
        return sorted(
            {r["metric"].get("service", "") for r in result if r["metric"].get("service")}
        )

    def range_values(
        self, expr: str, minutes: int = 30, step: str = "30s", max_series: int = 12
    ) -> dict[str, list[float]]:
        """Raw per-series values (for the anomaly detector; not exposed to the model)."""
        end = time.time()
        start = end - minutes * 60
        resp = httpx.get(
            f"{self.base}/api/v1/query_range",
            params={"query": expr, "start": start, "end": end, "step": step},
            timeout=self.timeout + 10,
        )
        resp.raise_for_status()
        out: dict[str, list[float]] = {}
        for item in resp.json()["data"]["result"][:max_series]:
            vals = [float(v[1]) for v in item["values"] if v[1] not in ("NaN", "+Inf", "-Inf")]
            if vals:
                out[_fmt_labels(item.get("metric", {}))] = vals
        return out


def _fmt_labels(metric: dict[str, str]) -> str:
    metric = {k: v for k, v in metric.items() if k != "__name__"}
    if not metric:
        return "{}"
    return "{" + ", ".join(f"{k}={v}" for k, v in sorted(metric.items())) + "}"


def _trend(values: list[float], rel: float = 0.1) -> Trend:
    """Compare first-third mean to last-third mean."""
    n = len(values)
    if n < 3:
        return "flat"
    third = max(1, n // 3)
    head = sum(values[:third]) / third
    tail = sum(values[-third:]) / third
    base = abs(head) if head else 1.0
    if tail > head * (1 + rel):
        return "rising"
    if tail < head * (1 - rel):
        return "falling"
    _ = base
    return "flat"
