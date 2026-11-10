"""Factory that builds a fully-wired mini-shop service.

Each service is tiny because this adds, in one place:
- OpenTelemetry tracing + JSON logs with trace ids
- Prometheus metrics (`/metrics`) and a health check (`/healthz`)
- fault middleware (error_rate, latency, dependency_timeout) + `/admin/faults`
"""

from __future__ import annotations

import asyncio
import logging
import random
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

from .faults import router as faults_router
from .faults import start_background_faults, state
from .logging_config import setup_logging
from .telemetry import setup_telemetry

_INFRA_PATHS = {"/healthz", "/metrics"}


def create_app(service_name: str) -> FastAPI:
    setup_logging(service_name)
    log = logging.getLogger(service_name)

    app = FastAPI(title=f"mini-shop · {service_name}")
    setup_telemetry(app, service_name)
    start_background_faults()

    # Per-app registry: each service process exposes only its own metrics,
    # and importing several services in one process can't collide.
    registry = CollectorRegistry()
    requests_total = Counter(
        "shop_http_requests_total",
        "HTTP requests",
        ["service", "method", "path", "status"],
        registry=registry,
    )
    request_latency = Histogram(
        "shop_http_request_duration_seconds",
        "HTTP request latency",
        ["service", "method", "path"],
        registry=registry,
    )

    @app.middleware("http")
    async def fault_and_metrics(request: Request, call_next):  # type: ignore[no-untyped-def]
        path = request.url.path
        faultable = path not in _INFRA_PATHS and not path.startswith("/admin")

        if faultable:
            delay = state.total_delay_s()
            if delay:
                await asyncio.sleep(delay)
            if state.error_rate and random.random() < state.error_rate:
                requests_total.labels(service_name, request.method, path, "500").inc()
                log.warning("injected error on %s", path)
                return JSONResponse({"detail": "injected fault"}, status_code=500)

        start = time.perf_counter()
        response = await call_next(request)
        request_latency.labels(service_name, request.method, path).observe(
            time.perf_counter() - start
        )
        requests_total.labels(service_name, request.method, path, str(response.status_code)).inc()
        return response

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "service": service_name}

    @app.get("/metrics")
    def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    app.include_router(faults_router)
    return app
