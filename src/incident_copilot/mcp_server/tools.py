"""The read-only investigation tools, as plain functions.

These are wrapped as MCP tools in server.py. Keeping them as functions makes them
unit-testable and callable directly during development.
"""

from __future__ import annotations

from typing import cast

from ..config import get_settings
from .anomaly.baseline import robust_zscore
from .backends import k8s
from .backends.prometheus import PrometheusClient
from .schemas import (
    AnomalyItem,
    AnomalyReport,
    Health,
    K8sEvent,
    K8sEvents,
    MetricSummary,
    PodLog,
    ServiceHealth,
)

_ERROR = 'shop_http_requests_total{{service="{s}",status=~"5.."}}'
_ALL = 'shop_http_requests_total{{service="{s}"}}'
_BUCKET = 'shop_http_request_duration_seconds_bucket{{service="{s}"}}'


def service_health(service: str, window: str = "5m") -> ServiceHealth:
    pc = PrometheusClient()
    rate = pc.scalar(f"sum(rate({_ALL.format(s=service)}[{window}]))") or 0.0
    err = pc.scalar(f"sum(rate({_ERROR.format(s=service)}[{window}]))") or 0.0
    error_rate = (err / rate) if rate > 0 else 0.0
    p95 = pc.scalar(
        f"histogram_quantile(0.95, sum by (le)(rate({_BUCKET.format(s=service)}[{window}])))"
    )

    if rate == 0.0:
        status: Health = "down"
        note = "no traffic observed in window"
    elif error_rate > 0.05 or (p95 is not None and p95 > 1.0):
        status = "degraded"
        note = (
            f"error_rate={error_rate:.0%}, p95={p95:.2f}s"
            if p95
            else f"error_rate={error_rate:.0%}"
        )
    else:
        status = "healthy"
        note = "within normal range"

    return ServiceHealth(
        service=service,
        request_rate=round(rate, 3),
        error_rate=round(error_rate, 4),
        p95_latency_s=round(p95, 3) if p95 is not None else None,
        status=status,
        note=note,
    )


def query_metrics(promql: str, window_minutes: int = 15) -> MetricSummary:
    pc = PrometheusClient()
    series, truncated = pc.range_summaries(promql, minutes=window_minutes)
    return MetricSummary(
        query=promql, window_minutes=window_minutes, series=series, truncated=truncated
    )


_METRIC_EXPR = {
    "error_rate": "sum(rate({err}[2m])) / clamp_min(sum(rate({all}[2m])), 0.001)",
    "p95_latency_s": "histogram_quantile(0.95, sum by (le)(rate({bucket}[2m])))",
    "request_rate": "sum(rate({all}[2m]))",
}
# Absolute magnitude floors: ignore deviations in trivially small metrics
# (e.g. a 0.008s p95 blip) that are statistically large but operationally irrelevant.
_FLOORS = {"error_rate": 0.03, "p95_latency_s": 0.1, "request_rate": 0.5}


def detect_anomalies(window_minutes: int = 30, threshold: float = 3.0) -> AnomalyReport:
    """Rank services/metrics deviating from their own baseline (robust z-score + magnitude floor).

    Errors are treated as inherently suspicious above the floor. A longer window keeps
    pre-incident normal data in the baseline so sustained shifts still register.
    """
    pc = PrometheusClient()
    found: list[AnomalyItem] = []
    for service in pc.list_services():
        exprs = {
            "err": _ERROR.format(s=service),
            "all": _ALL.format(s=service),
            "bucket": _BUCKET.format(s=service),
        }
        for metric_name, template in _METRIC_EXPR.items():
            values = next(
                iter(pc.range_values(template.format(**exprs), minutes=window_minutes).values()),
                [],
            )
            if not values or values[-1] < _FLOORS[metric_name]:
                continue  # below the magnitude floor — not worth flagging
            score = robust_zscore(values)
            if metric_name == "error_rate":
                # Meaningful error rates are suspicious regardless of window shape.
                score = max(score, values[-1] / 0.05 * 3.0)
            if score >= threshold:
                found.append(
                    AnomalyItem(
                        service=service,
                        metric=metric_name,
                        score=round(score, 2),
                        detail=f"latest={values[-1]:.4g}",
                    )
                )
    found.sort(key=lambda a: a.score, reverse=True)
    return AnomalyReport(
        window_minutes=window_minutes,
        method="robust_zscore(median/MAD) + magnitude floor",
        anomalies=found,
    )


def pod_logs(service: str, previous: bool = False, tail_lines: int = 40) -> PodLog:
    """Recent stdout/stderr for a service's pod (set previous=True for a crashed container)."""
    ns = get_settings().shop_namespace
    tail_lines = min(tail_lines, 100)  # token cap
    pod, lines = k8s.read_pod_logs(ns, service, previous=previous, tail_lines=tail_lines)
    truncated = len(lines) >= tail_lines
    return PodLog(service=service, pod=pod, previous=previous, lines=lines, truncated=truncated)


def k8s_events(limit: int = 20) -> K8sEvents:
    """Recent Warning events (OOMKilled, BackOff, FailedScheduling, ...) in the shop namespace."""
    ns = get_settings().shop_namespace
    raw = k8s.list_warning_events(ns, limit=limit)
    events = [
        K8sEvent(
            type=str(e["type"]),
            reason=str(e["reason"]),
            object=str(e["object"]),
            message=str(e["message"]),
            count=cast(int, e["count"]),
            last_seen=cast("str | None", e["last_seen"]),
        )
        for e in raw
    ]
    return K8sEvents(namespace=ns, events=events, truncated=len(raw) >= limit)
