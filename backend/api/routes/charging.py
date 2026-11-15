"""HTTP endpoints for charging."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.charging import history as charging_history
from backend.charging.ocpp_central import CentralChargePoint, SocketAdapter
from backend.charging.ocpp_registry import registry

router = APIRouter(tags=["charging"])


@router.get("/api/sessions")
def get_sessions(at: str | None = None, wallbox_id: str | None = None, limit: int = 50):
    return charging_history.sessions(at, wallbox_id, limit)


@router.get("/api/chargers/ocpp")
def ocpp_charge_points():
    return registry.snapshot()


@router.websocket("/ocpp/{charge_point_id}")
async def ocpp_socket(websocket: WebSocket, charge_point_id: str):
    await websocket.accept(subprotocol="ocpp1.6")
    charge_point = CentralChargePoint(charge_point_id, SocketAdapter(websocket))
    try:
        await charge_point.start()
    except WebSocketDisconnect:
        pass
    finally:
        registry.disconnect(charge_point_id)


@router.get("/api/chargers/{wallbox_id}/trend")
def get_charger_trend(wallbox_id: str, at: str | None = None, hours: int = 24):
    return charging_history.charger_trend(wallbox_id, at, hours)
