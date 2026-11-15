"""OCPP 1.6 JSON central system for charge points that connect to this twin."""

from __future__ import annotations

from datetime import datetime, timezone

from ocpp.routing import on
from ocpp.v16 import ChargePoint, call_result
from ocpp.v16.datatypes import IdTagInfo
from ocpp.v16.enums import Action, AuthorizationStatus, RegistrationStatus

from backend.charging.ocpp_registry import registry


class SocketAdapter:
    def __init__(self, websocket):
        self.websocket = websocket

    async def recv(self) -> str:
        return await self.websocket.receive_text()

    async def send(self, message: str) -> None:
        await self.websocket.send_text(message)


class CentralChargePoint(ChargePoint):
    @on(Action.boot_notification)
    async def on_boot_notification(self, charge_point_vendor: str, charge_point_model: str, **kwargs):
        record = registry.touch(self.id)
        record.vendor = charge_point_vendor
        record.model = charge_point_model
        record.status = "Available"
        return call_result.BootNotification(
            current_time=_now(),
            interval=60,
            status=RegistrationStatus.accepted,
        )

    @on(Action.heartbeat)
    async def on_heartbeat(self, **kwargs):
        registry.touch(self.id)
        return call_result.Heartbeat(current_time=_now())

    @on(Action.status_notification)
    async def on_status_notification(self, connector_id: int, status: str, **kwargs):
        record = registry.touch(self.id)
        record.connector_id = connector_id
        record.status = status
        return call_result.StatusNotification()

    @on(Action.start_transaction)
    async def on_start_transaction(
        self,
        connector_id: int,
        id_tag: str,
        meter_start: int,
        timestamp: str,
        **kwargs,
    ):
        record = registry.touch(self.id)
        record.transaction_id = registry.next_transaction()
        record.id_tag = id_tag
        record.connector_id = connector_id
        record.meter_wh = float(meter_start)
        record.status = "Charging"
        record.last_seen = timestamp
        return call_result.StartTransaction(
            transaction_id=record.transaction_id,
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted),
        )

    @on(Action.meter_values)
    async def on_meter_values(self, connector_id: int, meter_value: list, **kwargs):
        record = registry.touch(self.id)
        record.connector_id = connector_id
        power_kw, energy_wh = _measurements(meter_value)
        if power_kw is not None:
            record.power_kw = round(power_kw, 3)
        if energy_wh is not None:
            record.meter_wh = energy_wh
        return call_result.MeterValues()

    @on(Action.stop_transaction)
    async def on_stop_transaction(self, meter_stop: int, timestamp: str, transaction_id: int, **kwargs):
        record = registry.touch(self.id)
        record.meter_wh = float(meter_stop)
        record.transaction_id = None
        record.status = "Finishing"
        record.last_seen = timestamp
        return call_result.StopTransaction(
            id_tag_info=IdTagInfo(status=AuthorizationStatus.accepted)
        )


def _measurements(meter_value: list) -> tuple[float | None, float | None]:
    power_kw = None
    energy_wh = None
    for sample in meter_value:
        for item in sample.get("sampled_value", []):
            measurand = item.get("measurand", "Energy.Active.Import.Register")
            value = float(item["value"])
            unit = item.get("unit", "Wh")
            if measurand == "Power.Active.Import":
                power_kw = value / 1000 if unit in {"W", "w"} else value
            elif measurand == "Energy.Active.Import.Register":
                energy_wh = value * 1000 if unit == "kWh" else value
    return power_kw, energy_wh


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
