"""Finite, ordered telemetry frames for the simulated MQTT transport."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TOPIC = "twin/SOFIE/demo/telemetry"


class ChargerReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=80)
    power_kw: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    status: str = Field(min_length=1, max_length=40)
    status_stale: bool = False


class TelemetryFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(pattern="^sofie-historical-demo$")
    run_id: UUID
    sequence: int = Field(ge=0)
    recorded_at: datetime
    emitted_at: datetime
    solar_kw: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    battery_soc_pct: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    battery_temp_c: float | None = Field(default=None, ge=-50, le=150, allow_inf_nan=False)
    wallboxes: list[ChargerReading] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_frame(self):
        if self.recorded_at.tzinfo is not None or self.emitted_at.tzinfo is None:
            raise ValueError(
                "recorded_at must be unzoned source time and emitted_at must be timezone-aware"
            )
        ids = [box.id for box in self.wallboxes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate wallbox id")
        return self
