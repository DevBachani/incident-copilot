"""Built-in, toggleable application faults.

A single in-process ``state`` holds the current fault settings. The protected
``/admin/faults`` endpoint (token from a K8s Secret in-cluster) turns them on/off.
The fault injector (``faults/inject.py``) drives this endpoint to create incidents.
"""

from __future__ import annotations

import os
import threading
import time

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dev-token")

_FAULT_FIELDS = (
    "error_rate",  # 0..1 fraction of requests that return HTTP 500
    "latency_ms",  # fixed delay added to each request
    "dependency_timeout_ms",  # extra delay (simulates a slow downstream dependency)
    "bad_data",  # return malformed responses that break callers
    "cpu_burn",  # busy-loop to saturate CPU
    "memory_leak",  # grow memory steadily until OOM
)


class _State:
    def __init__(self) -> None:
        self.error_rate: float = 0.0
        self.latency_ms: int = 0
        self.dependency_timeout_ms: int = 0
        self.bad_data: bool = False
        self.cpu_burn: bool = False
        self.memory_leak: bool = False
        self._leak: list[bytearray] = []

    def snapshot(self) -> dict[str, object]:
        return {field: getattr(self, field) for field in _FAULT_FIELDS}

    def total_delay_s(self) -> float:
        return (self.latency_ms + self.dependency_timeout_ms) / 1000.0


state = _State()


def _background_loop() -> None:
    """Drive cpu_burn and memory_leak faults from one daemon thread."""
    while True:
        if state.cpu_burn:
            end = time.time() + 0.05
            while time.time() < end:  # busy loop — contends the GIL, raises CPU
                pass
        if state.memory_leak:
            state._leak.append(bytearray(1024 * 1024))  # +1 MB each tick
        time.sleep(0.1)


_started = False


def start_background_faults() -> None:
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_background_loop, daemon=True).start()


class FaultUpdate(BaseModel):
    error_rate: float | None = None
    latency_ms: int | None = None
    dependency_timeout_ms: int | None = None
    bad_data: bool | None = None
    cpu_burn: bool | None = None
    memory_leak: bool | None = None


router = APIRouter(prefix="/admin")


def _auth(token: str) -> None:
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="invalid admin token")


@router.get("/faults")
def get_faults(x_admin_token: str = Header(...)) -> dict[str, object]:
    _auth(x_admin_token)
    return state.snapshot()


@router.post("/faults")
def set_faults(update: FaultUpdate, x_admin_token: str = Header(...)) -> dict[str, object]:
    _auth(x_admin_token)
    for key, value in update.model_dump(exclude_none=True).items():
        setattr(state, key, value)
    if not state.memory_leak:
        state._leak.clear()  # releasing the leak lets memory recover
    return state.snapshot()
