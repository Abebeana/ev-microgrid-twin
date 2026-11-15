"""Validated microgrid inventory, limits, and time interpretation."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.configuration.paths import PROJECT_ROOT

DEFAULT_CONFIG = PROJECT_ROOT / "config/site.json"


class AssetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    kind: Literal["solar", "battery", "bus", "other"]
    connected_to: str | None = None


class SiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    site_id: str
    site_name: str
    site_timezone: str
    source_timestamp_timezone: str
    source_timezone_evidence: str
    default_replay_at: str
    islanded: bool = True
    assets: list[AssetConfig] = Field(min_length=1)
    battery_capacity_kwh: float = Field(gt=0)
    battery_max_power_kw: float = Field(gt=0)
    battery_min_soc_pct: float = Field(ge=0, lt=100)
    battery_model_efficiency: float = Field(gt=0, le=1)
    battery_model_efficiency_note: str
    latitude_deg: float = Field(default=52.52, ge=-90, le=90)
    longitude_deg: float = Field(default=13.405, ge=-180, le=180)
    location_assumption: str = (
        "Berlin coordinates stand in until the data owner confirms the SOFIE site."
    )
    pv_tilt_deg: float = Field(default=15, ge=0, le=90)
    pv_azimuth_deg: float = Field(default=180, ge=0, lt=360)
    pv_nameplate_kw: float = Field(default=100, gt=0)
    pv_nameplate_note: str = (
        "Clip for the physical PV model. This matches the validation ceiling, not a verified nameplate."
    )
    solar_validation_max_kw: float = Field(gt=0)
    charger_validation_max_kw: float = Field(gt=0)
    battery_temperature_min_c: float
    battery_temperature_max_c: float
    optimizer_min_coverage_pct: float = Field(gt=0, le=100)
    optimizer_step_minutes: int = Field(ge=1, le=60)
    optimizer_unserved_weight: float = Field(gt=0)
    optimizer_curtailment_weight: float = Field(gt=0)
    optimizer_throughput_weight: float = Field(gt=0)
    charger_stale_minutes: int = Field(gt=0)
    battery_low_soc_alarm_pct: float = Field(ge=0, le=100)
    battery_high_temp_alarm_c: float
    grid_connection: dict | None = None
    tariff: dict | None = None
    weather_source: dict | None = None
    forecast_source: dict | None = None
    live_source: dict | None = None
    control_integration: dict | None = None

    @field_validator("site_timezone", "source_timestamp_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @model_validator(mode="after")
    def validate_island(self) -> "SiteConfig":
        if self.islanded and self.grid_connection is not None:
            raise ValueError("An islanded site cannot declare a grid connection")
        if self.battery_temperature_min_c >= self.battery_temperature_max_c:
            raise ValueError("Battery temperature validation bounds are reversed")
        if datetime.fromisoformat(self.default_replay_at).tzinfo is None:
            raise ValueError("default_replay_at needs a timezone offset")
        ids = [asset.id for asset in self.assets]
        if len(ids) != len(set(ids)) or sum(asset.kind == "bus" for asset in self.assets) != 1:
            raise ValueError("Asset ids must be unique and exactly one islanded AC bus is required")
        if any(
            asset.connected_to not in (None, *ids) or asset.connected_to == asset.id
            for asset in self.assets
        ):
            raise ValueError("Asset connections must refer to another configured asset")
        if 60 % self.optimizer_step_minutes:
            raise ValueError("optimizer_step_minutes must divide one hour")
        return self


def load_site_config() -> SiteConfig:
    path = Path(os.environ.get("TWIN_SITE_CONFIG", DEFAULT_CONFIG))
    return SiteConfig.model_validate(json.loads(path.read_text()))
