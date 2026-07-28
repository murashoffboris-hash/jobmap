"""Prometheus metrics for FastAPI — exposed at /metrics."""

from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import latency
from fastapi import FastAPI


def setup_metrics(app: FastAPI) -> Instrumentator:
    """Attach Prometheus metrics middleware to the FastAPI app.

    Exposes /metrics endpoint with:
      - http_request_duration_seconds (p50/p90/p95/p99)
      - http_requests_total (by method, path, status)
      - http_request_size_bytes
    """
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

    return instrumentator
