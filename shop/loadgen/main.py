"""loadgen — generates steady traffic against the frontend.

Run as a plain script (not a web server):  python -m shop.loadgen.main
"""

from __future__ import annotations

import os
import random
import time

import httpx

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:8000")
RPS = float(os.getenv("LOADGEN_RPS", "5"))
_interval = 1.0 / RPS if RPS > 0 else 0.2


def main() -> None:
    print(f"loadgen -> {FRONTEND_URL} at ~{RPS} rps", flush=True)
    with httpx.Client(timeout=10) as client:
        while True:
            try:
                if random.random() < 0.3:
                    client.post(f"{FRONTEND_URL}/buy")
                else:
                    client.get(f"{FRONTEND_URL}/")
            except Exception as exc:  # noqa: BLE001 - keep generating load through errors
                print(f"loadgen error: {exc}", flush=True)
            time.sleep(_interval)


if __name__ == "__main__":
    main()
