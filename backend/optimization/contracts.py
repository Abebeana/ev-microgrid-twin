"""Validated inputs for historical dispatch scenarios."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScenarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    start: str
    hours: int = Field(ge=1, le=24)
    charging_multiplier: float = Field(default=1, ge=0, le=2)
    solar_multiplier: float = Field(default=1, ge=0, le=2)
    battery_capacity_kwh: float | None = Field(default=None, gt=0, le=200)
    outage_wallbox_id: str | None = None
