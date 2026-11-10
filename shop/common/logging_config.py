"""Structured JSON logging with trace ids.

Every log line is one JSON object carrying the service name and, when a span is
active, the OpenTelemetry trace id — so logs in Loki can be correlated with traces.
"""

from __future__ import annotations

import json
import logging
import sys
import time

from opentelemetry import trace


class _JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        span = trace.get_current_span()
        ctx = span.get_span_context() if span else None
        if ctx and ctx.trace_id:
            payload["trace_id"] = format(ctx.trace_id, "032x")
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def setup_logging(service_name: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter(service_name))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
