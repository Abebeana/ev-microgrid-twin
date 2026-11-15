"""Request metrics and the Prometheus scrape endpoint."""

from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

log = logging.getLogger(__name__)
REQUESTS = Counter("twin_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("twin_http_request_seconds", "HTTP request duration", ["route"])
router = APIRouter(tags=["metrics"])


async def observe(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("Request failed: %s %s", request.method, request.url.path)
        raise
    route = getattr(request.scope.get("route"), "path", request.url.path)
    REQUESTS.labels(request.method, route, str(response.status_code)).inc()
    LATENCY.labels(route).observe(time.perf_counter() - start)
    return response


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
