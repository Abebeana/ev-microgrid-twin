"""Register feature routers in one explicit API boundary."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api import metrics
from backend.api.routes import (
    alarms,
    audit,
    charging,
    electrical,
    forecasts,
    health,
    reinforcement_learning,
    scenarios,
    storage,
    streaming,
    telemetry,
    topology,
)

router = APIRouter()

for feature in (
    health,
    telemetry,
    charging,
    alarms,
    scenarios,
    forecasts,
    electrical,
    storage,
    streaming,
    audit,
    topology,
    reinforcement_learning,
    metrics,
):
    router.include_router(feature.router)
