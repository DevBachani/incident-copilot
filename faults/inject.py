"""Fault injector — turns scenario faults on/off and records ground truth.

Usage:
    uv run python faults/inject.py inject payment-errors-01
    uv run python faults/inject.py clear  payment-errors-01
    uv run python faults/inject.py clear-all
    uv run python faults/inject.py list

App faults are applied through each service's token-protected /admin/faults
endpoint (reached via a short-lived `kubectl port-forward`). Ground truth for
every injection is appended to faults/ground_truth.jsonl for objective scoring.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

SCENARIO_DIR = Path(__file__).parent / "scenarios"
GROUND_TRUTH = Path(__file__).parent / "ground_truth.jsonl"
NAMESPACE = os.getenv("SHOP_NAMESPACE", "shop")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-token")

# A fault's "off" value, used by `clear`.
OFF = {
    "error_rate": 0.0,
    "latency_ms": 0,
    "dependency_timeout_ms": 0,
    "bad_data": False,
    "cpu_burn": False,
    "memory_leak": False,
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def port_forward(service: str, remote: int = 8000) -> Iterator[str]:
    local = _free_port()
    proc = subprocess.Popen(
        ["kubectl", "port-forward", f"svc/{service}", "-n", NAMESPACE, f"{local}:{remote}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 15
        while time.time() < deadline:
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", local), 1):
                break
            time.sleep(0.3)
        else:
            raise TimeoutError(f"port-forward to {service} never became ready")
        yield f"http://127.0.0.1:{local}"
    finally:
        proc.terminate()


def set_fault(service: str, fault: str, value: object) -> dict:
    with port_forward(service) as base:
        resp = httpx.post(
            f"{base}/admin/faults",
            json={fault: value},
            headers={"x-admin-token": ADMIN_TOKEN},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()


def load_scenario(scenario_id: str) -> dict:
    path = SCENARIO_DIR / f"{scenario_id}.yaml"
    if not path.exists():
        sys.exit(f"no scenario file: {path}")
    return yaml.safe_load(path.read_text())


def record_ground_truth(scenario: dict, action: str) -> None:
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "scenario_id": scenario["id"],
        "root_cause_service": scenario["expected"]["root_cause_service"],
        "root_cause_category": scenario["expected"]["root_cause_category"],
    }
    with GROUND_TRUTH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def cmd_inject(scenario_id: str) -> None:
    sc = load_scenario(scenario_id)
    inj = sc["inject"]
    if inj["type"] != "app_fault":
        sys.exit(f"infra faults not yet supported by this command: {inj['type']}")
    state = set_fault(inj["service"], inj["fault"], inj["value"])
    record_ground_truth(sc, "inject")
    print(f"injected {scenario_id}: {inj['service']}.{inj['fault']}={inj['value']}")
    print(f"  {inj['service']} fault state: {state}")


def cmd_clear(scenario_id: str) -> None:
    sc = load_scenario(scenario_id)
    inj = sc["inject"]
    set_fault(inj["service"], inj["fault"], OFF[inj["fault"]])
    record_ground_truth(sc, "clear")
    print(f"cleared {scenario_id}: {inj['service']}.{inj['fault']}")


def cmd_clear_all() -> None:
    services = {s.stem.split("-")[0] for s in SCENARIO_DIR.glob("*.yaml")}
    for sc_file in SCENARIO_DIR.glob("*.yaml"):
        inj = yaml.safe_load(sc_file.read_text())["inject"]
        services.add(inj["service"])
    for service in sorted(services):
        with contextlib.suppress(Exception):
            set_fault(service, "error_rate", 0.0)
            for fault, off in OFF.items():
                set_fault(service, fault, off)
            print(f"cleared all faults on {service}")


def cmd_list() -> None:
    for sc_file in sorted(SCENARIO_DIR.glob("*.yaml")):
        sc = yaml.safe_load(sc_file.read_text())
        print(f"{sc['id']:24} {sc.get('difficulty', '?'):7} {sc.get('description', '')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject/clear mini-shop faults")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inject", "clear"):
        p = sub.add_parser(name)
        p.add_argument("scenario_id")
    sub.add_parser("clear-all")
    sub.add_parser("list")
    args = parser.parse_args()

    if args.command == "inject":
        cmd_inject(args.scenario_id)
    elif args.command == "clear":
        cmd_clear(args.scenario_id)
    elif args.command == "clear-all":
        cmd_clear_all()
    elif args.command == "list":
        cmd_list()


if __name__ == "__main__":
    main()
