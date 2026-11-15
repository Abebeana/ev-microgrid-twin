"""HTTP endpoints for electrical studies."""

from __future__ import annotations

from fastapi import APIRouter

from backend.electrical import network
from backend.telemetry import history

router = APIRouter(tags=["electrical"])


@router.get("/api/electrical/power-flow")
def power_flow(at: str | None = None):
    snapshot = history.snapshot(at)
    chargers = [(box["id"], box["power_kw"]) for box in snapshot["wallboxes"]]
    result = network.solve(snapshot["solar_kw"], chargers)
    result["raw_time"] = snapshot["raw_time"]
    result["site_time"] = snapshot["site_time"]
    return result
