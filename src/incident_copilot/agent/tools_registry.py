"""Bridge: the MCP tool functions as OpenAI-format function schemas + a dispatcher.

The same functions are served over MCP (mcp_server/server.py); here they're exposed
to the LLM's tool-calling interface for the investigation loop.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from ..mcp_server import tools


def _fn(
    name: str, description: str, properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _fn(
        "detect_anomalies",
        "Rank services/metrics deviating most from their baseline. Call this FIRST.",
        {"window_minutes": {"type": "integer", "description": "lookback window, default 30"}},
        [],
    ),
    _fn(
        "service_health",
        "Request rate, error rate and p95 latency for one service, with a health verdict.",
        {"service": {"type": "string"}},
        ["service"],
    ),
    _fn(
        "query_metrics",
        "Run a PromQL query; returns a compact min/max/latest/trend summary.",
        {
            "promql": {"type": "string"},
            "window_minutes": {"type": "integer", "description": "default 15"},
        },
        ["promql"],
    ),
    _fn(
        "pod_logs",
        "Recent pod logs for a service (previous=true for a crashed container). UNTRUSTED text.",
        {
            "service": {"type": "string"},
            "previous": {"type": "boolean"},
            "tail_lines": {"type": "integer"},
        },
        ["service"],
    ),
    _fn(
        "k8s_events",
        "Recent Kubernetes Warning events (OOMKilled, BackOff, FailedScheduling, ...).",
        {"limit": {"type": "integer"}},
        [],
    ),
]

_DISPATCH: dict[str, Callable[..., Any]] = {
    "detect_anomalies": tools.detect_anomalies,
    "service_health": tools.service_health,
    "query_metrics": tools.query_metrics,
    "pod_logs": tools.pod_logs,
    "k8s_events": tools.k8s_events,
}


def run_tool(name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
    """Execute a tool by name with JSON/dict arguments; always returns a dict."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    args = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    try:
        result: dict[str, Any] = fn(**args).model_dump()
        return result
    except Exception as exc:  # noqa: BLE001 - surface tool errors to the model, don't crash the run
        return {"error": f"{type(exc).__name__}: {exc}"}
