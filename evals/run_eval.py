"""Evaluate the agent across scenarios in replay mode, with honest statistics.

    uv run python evals/run_eval.py --k 3

Runs each scenario that has recorded fixtures k times, scores against ground truth,
and reports top-1/top-3 accuracy with Wilson 95% CIs, pass^k reliability, fixture
miss rate and token/latency medians. Writes JSON + a markdown table to evals/results/.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml
from scorers import score_report, wilson_interval

from incident_copilot.agent.run import alert_for_scenario, diagnose
from incident_copilot.replay.store import FixtureStore

FIXTURES = Path("evals/fixtures")
RESULTS = Path("evals/results")


def _expected(scenario_id: str) -> dict:
    sc = yaml.safe_load(Path(f"faults/scenarios/{scenario_id}.yaml").read_text())
    return sc["expected"]


def run_scenario(scenario_id: str, k: int) -> list[dict]:
    alert = alert_for_scenario(scenario_id)
    expected = _expected(scenario_id)
    runs: list[dict] = []
    for _ in range(k):
        store = FixtureStore(scenario_id)
        store.load()
        try:
            out = diagnose(alert, tool_fn=store.replay)
            scored = score_report(out["report"], expected)
            scored.update(
                miss_rate=store.miss_rate,
                tokens=out["stats"]["tokens"],
                seconds=out["stats"]["seconds"],
            )
        except Exception as exc:  # noqa: BLE001 - a crashed run counts as a miss, not a stop
            scored = {"top1": False, "top3": False, "action": False, "error": str(exc)[:120]}
        runs.append(scored)
    return runs


def aggregate(results: dict[str, list[dict]]) -> dict:
    all_runs = [r for runs in results.values() for r in runs]
    n = len(all_runs)
    top1 = sum(r["top1"] for r in all_runs)
    top3 = sum(r["top3"] for r in all_runs)
    action = sum(r.get("action", False) for r in all_runs)
    # pass^k: scenarios correct (top-3) on EVERY run
    passk = sum(all(r["top3"] for r in runs) for runs in results.values())
    tokens = [r["tokens"] for r in all_runs if "tokens" in r]
    secs = [r["seconds"] for r in all_runs if "seconds" in r]
    misses = [r["miss_rate"] for r in all_runs if "miss_rate" in r]
    return {
        "runs": n,
        "scenarios": len(results),
        "top1": wilson_interval(top1, n),
        "top3": wilson_interval(top3, n),
        "action_rate": round(action / n, 3) if n else 0.0,
        "passk_scenarios": f"{passk}/{len(results)}",
        "median_tokens": round(statistics.median(tokens)) if tokens else None,
        "median_seconds": round(statistics.median(secs), 1) if secs else None,
        "mean_fixture_miss_rate": round(statistics.mean(misses), 3) if misses else None,
    }


def _markdown(agg: dict, k: int) -> str:
    def ci(t: tuple) -> str:
        return f"{t[0]:.0%} ({t[1]:.0%}–{t[2]:.0%})"

    return (
        f"# Eval results\n\n"
        f"_{agg['scenarios']} scenarios × k={k} = {agg['runs']} runs, replay mode._\n\n"
        f"| Metric | Value |\n|---|---|\n"
        f"| Top-1 accuracy (service+category) | {ci(agg['top1'])} |\n"
        f"| Top-3 accuracy | {ci(agg['top3'])} |\n"
        f"| Action correctness | {agg['action_rate']:.0%} |\n"
        f"| pass^k (correct every run) | {agg['passk_scenarios']} |\n"
        f"| Median tokens / incident | {agg['median_tokens']} |\n"
        f"| Median time to diagnosis | {agg['median_seconds']}s |\n"
        f"| Mean fixture-miss rate | {agg['mean_fixture_miss_rate']} |\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the agent in replay mode")
    parser.add_argument("--k", type=int, default=1, help="repeats per scenario")
    args = parser.parse_args()

    scenario_ids = sorted(p.stem for p in FIXTURES.glob("*.json"))
    if not scenario_ids:
        raise SystemExit("no fixtures found — record some first (--mode record)")

    results = {sid: run_scenario(sid, args.k) for sid in scenario_ids}
    agg = aggregate(results)

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (RESULTS / f"eval-{stamp}.json").write_text(
        json.dumps(
            {"ts": time.time(), "k": args.k, "aggregate": agg, "per_scenario": results}, indent=2
        )
    )
    md = _markdown(agg, args.k)
    (RESULTS / "latest.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
