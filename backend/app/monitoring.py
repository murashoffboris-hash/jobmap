"""Prometheus metrics for FastAPI — exposed at /metrics."""

import logging

from fastapi import FastAPI
from prometheus_client import REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import latency

logger = logging.getLogger(__name__)

# Sentinel to ensure setup_metrics runs at most once per process.
# Prometheus metrics are global singletons — re-registering the
# same Gauge/Histogram name raises ValueError.
_metrics_installed: bool = False


def setup_metrics(app: FastAPI) -> Instrumentator | None:
    """Attach Prometheus metrics middleware to the FastAPI app.

    Idempotent — safe to call multiple times (e.g. in tests where
    ``create_app()`` is invoked per test case).  Only the first call
    actually registers metrics with the global Prometheus registry.

    Exposes /metrics endpoint with:
      - http_request_duration_seconds (p50/p90/p95/p99)
      - http_requests_total (by method, path, status)
      - http_request_size_bytes
    """
    global _metrics_installed

    # Already registered — skip so tests calling create_app() repeatedly
    # don't hit "Duplicated timeseries in CollectorRegistry".
    if _metrics_installed:
        return None

    # Double-check the global registry in case another module installed
    # metrics before us (belt-and-suspenders for mixed test suites).
    if "http_requests_inprogress" in REGISTRY._names_to_collectors:
        _metrics_installed = True
        logger.debug("Prometheus metrics already registered — skipping.")
        return None

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health", "/api/docs", "/api/redoc", "/api/openapi.json"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add latency histogram buckets suitable for web APIs (ms → seconds)
    instrumentator.add(
        latency(
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            metric_name="http_request_duration_seconds",
        )
    )

    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    _metrics_installed = True

    return instrumentator
