"""HTTP endpoints for forecasts."""

from __future__ import annotations

from fastapi import APIRouter

from backend.forecasting import persistence, physical

router = APIRouter(tags=["forecasts"])


@router.get("/api/forecasts/baseline")
def forecast_baseline(at: str | None = None):
    return persistence.baseline(at)


@router.get("/api/forecasts/physical")
def physical_forecast(at: str | None = None):
    return physical.forecast(at)
