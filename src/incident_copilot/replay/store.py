"""FixtureStore — records tool (name, args) -> result pairs, and replays them.

Keys use normalized arguments (sorted keys, canonical PromQL spacing) and only
relative time windows (window_minutes), never absolute timestamps, so a recorded
call matches on replay.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..agent.tools_registry import run_tool

FIXTURES_DIR = Path("evals/fixtures")

# Standard calls recorded during priming so replay covers calls a future agent
# version might make (not just the ones this run happened to make).
_SERVICES = ["frontend", "catalog", "cart", "checkout", "payment"]

# Common PromQL the agent tends to ask for — primed so replay covers them.
_STANDARD_PROMQL = [
    "sum by (service)(rate(shop_http_requests_total[5m]))",
    'sum by (service)(rate(shop_http_requests_total{status=~"5.."}[5m]))',
    "histogram_quantile(0.95, sum by (service, le)"
    "(rate(shop_http_request_duration_seconds_bucket[5m])))",
]


def _normalize(name: str, arguments: str | dict[str, Any]) -> str:
    args = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    if "promql" in args and isinstance(args["promql"], str):
        args["promql"] = " ".join(args["promql"].split())
    return f"{name}::{json.dumps(args, sort_keys=True)}"


class FixtureStore:
    def __init__(self, scenario_id: str, fixtures_dir: Path = FIXTURES_DIR) -> None:
        self.scenario_id = scenario_id
        self.path = fixtures_dir / f"{scenario_id}.json"
        self.data: dict[str, Any] = {}
        self.calls = 0
        self.misses = 0

    # --- live recording ---
    def record(self, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        result = run_tool(name, arguments)
        self.data[_normalize(name, arguments)] = result
        return result

    def prime(self) -> None:
        """Record a standard set of calls for every service, broadening replay coverage."""
        self.record("detect_anomalies", {})
        self.record("k8s_events", {})
        for svc in _SERVICES:
            self.record("service_health", {"service": svc})
            self.record("pod_logs", {"service": svc})
            self.record("pod_logs", {"service": svc, "previous": True})
        for promql in _STANDARD_PROMQL:
            self.record("query_metrics", {"promql": promql})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))

    # --- replay ---
    def load(self) -> None:
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def replay(self, name: str, arguments: str | dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        key = _normalize(name, arguments)
        if key in self.data:
            cached: dict[str, Any] = self.data[key]
            return cached
        self.misses += 1
        return {"no_recorded_data": True, "tool": name}

    @property
    def miss_rate(self) -> float:
        return self.misses / self.calls if self.calls else 0.0
