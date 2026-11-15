"""Run the diagnosis agent on one alert — live, recording, or replay.

# live against the cluster
uv run python -m incident_copilot.agent.run --service payment --symptom "high error rate"
# record fixtures for a scenario (cluster up)
uv run python -m incident_copilot.agent.run --scenario payment-errors-01 --mode record
# replay (cluster can be stopped)
uv run python -m incident_copilot.agent.run --scenario payment-errors-01 --mode replay
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import yaml

from ..llm.router import LLMRouter
from ..replay.store import FixtureStore
from .graph import build_graph
from .tools_registry import run_tool

_SYMPTOM = {
    "error_rate": "high error rate",
    "latency_ms": "elevated latency",
    "dependency_timeout_ms": "elevated latency",
    "bad_data": "clients failing to parse responses",
    "cpu_burn": "high latency / CPU saturation",
    "memory_leak": "rising memory / restarts",
}


def alert_for_scenario(scenario_id: str) -> dict[str, Any]:
    sc = yaml.safe_load(Path(f"faults/scenarios/{scenario_id}.yaml").read_text())
    inj = sc["inject"]
    # Alert names the service the alert fired on + a generic symptom (never the cause).
    return {
        "service": sc.get("alert_service", inj["service"]),
        "symptom": _SYMPTOM.get(inj["fault"], "anomaly detected"),
    }


def diagnose(alert: dict[str, Any], tool_fn: Any = run_tool) -> dict[str, Any]:
    router = LLMRouter()
    app = build_graph(router, tool_fn=tool_fn)
    start = time.time()
    final = app.invoke(
        {"alert": alert, "messages": [], "tool_calls": 0, "report": None},
        config={"recursion_limit": 40},
    )
    return {
        "report": final["report"],
        "stats": {
            "tool_calls": final["tool_calls"],
            "llm_calls": router.calls,
            "tokens": router.tokens,
            "model": router.last_model,
            "seconds": round(time.time() - start, 1),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose an incident")
    parser.add_argument("--scenario")
    parser.add_argument("--service", default="payment")
    parser.add_argument("--symptom", default="high error rate")
    parser.add_argument("--mode", choices=["live", "record", "replay"], default="live")
    args = parser.parse_args()

    alert = (
        alert_for_scenario(args.scenario)
        if args.scenario
        else {
            "service": args.service,
            "symptom": args.symptom,
        }
    )

    store: FixtureStore | None = None
    tool_fn: Any = run_tool
    if args.mode in ("record", "replay"):
        if not args.scenario:
            parser.error("--scenario is required for record/replay")
        store = FixtureStore(args.scenario)
        if args.mode == "record":
            store.prime()
            store.save()  # persist primed fixtures even if the agent run later fails
            tool_fn = store.record
        else:
            store.load()
            tool_fn = store.replay

    out = diagnose(alert, tool_fn=tool_fn)
    if store is not None and args.mode == "record":
        store.save()
        out["fixtures_saved"] = len(store.data)
    if store is not None and args.mode == "replay":
        out["fixture_miss_rate"] = round(store.miss_rate, 3)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
