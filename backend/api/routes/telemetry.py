"""HTTP endpoints for telemetry."""

from __future__ import annotations

from fastapi import APIRouter

from backend.telemetry import history

router = APIRouter(tags=["telemetry"])


@router.get("/api/site")
def get_site():
    return history.site()


@router.get("/api/replay")
def get_replay(at: str | None = None):
    return history.snapshot(at)


@router.get("/api/trend")
def get_trend(at: str | None = None, hours: int = 24):
    return history.trend(at, hours)


@router.get("/api/quality")
def get_quality():
    return history.quality()
