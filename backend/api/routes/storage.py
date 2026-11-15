"""HTTP endpoints for battery studies."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.battery import pack
from backend.configuration.site import load_site_config
from backend.telemetry import history

router = APIRouter(tags=["storage"])


@router.get("/api/battery/model")
def battery_model(at: str | None = None):
    snapshot = history.snapshot(at)
    if snapshot["battery_soc_pct"] is None:
        raise HTTPException(422, "Battery state of charge is missing at this minute")
    config = load_site_config()
    solar = snapshot["solar_kw"] or 0
    charging = snapshot["observed_charging_kw"] or 0
    if snapshot["solar_kw"] is None and snapshot["observed_charging_kw"] is None:
        power_kw = 0.0
    else:
        power_kw = max(-config.battery_max_power_kw, min(config.battery_max_power_kw, charging - solar))
    result = pack.simulate(
        pack_kwh=config.battery_capacity_kwh,
        soc_pct=snapshot["battery_soc_pct"],
        power_kw=power_kw,
        ambient_c=snapshot["battery_temp_c"],
    )
    result["raw_time"] = snapshot["raw_time"]
    result["site_time"] = snapshot["site_time"]
    result["solar_measured"] = snapshot["solar_kw"] is not None
    result["charging_measured"] = snapshot["observed_charging_kw"] is not None
    return result
