"""HTTP endpoints for health."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.telemetry import history
from backend.topology.neo4j_store import graph_store

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    try:
        graph = graph_store.ping()
        if not graph["connected"]:
            raise HTTPException(503, "Neo4j is required and unavailable")
        site = history.site()
        return {
            "status": "ok",
            "mode": "historical_replay",
            "source": site["metadata"]["source_filename"],
            "live_connected": site["live_connected"],
            "wallboxes": len(site["wallboxes"]),
            "graph": graph,
        }
    except HTTPException as error:
        raise HTTPException(503, error.detail) from error


@router.get("/api/availability")
def availability():
    return {
        "baseline": {
            "available": True,
            "reason": "Historical persistence model with paired error checks",
        },
        "forecast": {
            "available": True,
            "reason": "Clear-sky PVWatts scaled to recorded PV, with an 80% conformal interval",
        },
        "weather": {"available": False, "reason": "No weather source in SOFIE"},
        "tariff": {
            "available": False,
            "reason": "No tariff in SOFIE; islanded dispatch has no grid purchase",
        },
        "control": {
            "available": False,
            "reason": "No physical control integration or approval process is connected",
        },
        "live": {
            "available": False,
            "reason": "No physical live source is connected; MQTT replay is a labeled simulation",
        },
    }
