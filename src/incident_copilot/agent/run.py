"""Run the diagnosis agent on one alert.

uv run python -m incident_copilot.agent.run --service payment --symptom "high error rate"
"""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from ..llm.router import LLMRouter
from .graph import build_graph


def diagnose(alert: dict[str, Any]) -> dict[str, Any]:
    router = LLMRouter()
    app = build_graph(router)
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
    parser.add_argument("--service", default="payment")
    parser.add_argument("--symptom", default="high error rate")
    args = parser.parse_args()
    out = diagnose({"service": args.service, "symptom": args.symptom})
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
