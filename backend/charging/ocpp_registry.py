"""In-memory state for charge points that connect over OCPP 1.6."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ChargePointRecord:
    charge_point_id: str
    vendor: str | None = None
    model: str | None = None
    status: str = "Connecting"
    connected: bool = False
    transaction_id: int | None = None
    id_tag: str | None = None
    meter_wh: float | None = None
    power_kw: float | None = None
    last_seen: str | None = None
    connector_id: int | None = None


@dataclass
class Registry:
    points: dict[str, ChargePointRecord] = field(default_factory=dict)
    _next_transaction: int = 1

    def touch(self, charge_point_id: str) -> ChargePointRecord:
        record = self.points.get(charge_point_id)
        if record is None:
            record = ChargePointRecord(charge_point_id=charge_point_id)
            self.points[charge_point_id] = record
        record.last_seen = datetime.now(timezone.utc).isoformat()
        record.connected = True
        return record

    def disconnect(self, charge_point_id: str) -> None:
        record = self.points.get(charge_point_id)
        if record is not None:
            record.connected = False
            record.status = "Disconnected"

    def next_transaction(self) -> int:
        transaction_id = self._next_transaction
        self._next_transaction += 1
        return transaction_id

    def snapshot(self) -> dict:
        return {
            "protocol": "OCPP 1.6 JSON",
            "socket": "/ocpp/{charge_point_id}",
            "charge_points": [asdict(record) for record in self.points.values()],
        }


registry = Registry()
