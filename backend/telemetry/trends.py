"""Aggregate historical trends without filling missing measurements."""

from datetime import timedelta

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time


def trend(at: str | None, hours: int) -> dict:
    if hours not in (6, 24, 72):
        raise HTTPException(422, "hours must be 6, 24, or 72")
    config = load_site_config()
    moment = source_time(at, config)
    start = raw_string(moment - timedelta(hours=hours))
    end = raw_string(moment)
    with replay_store() as store:
        solar_rows = store.between("microgrid_minute", start, end)
        charger_rows = store.charging_totals(start, end)
    charging = {r["raw_minute"]: (r["power_kw"], r["boxes"]) for r in charger_rows}
    stride = 5 if hours == 6 else 15 if hours == 24 else 30
    bins: dict[str, dict] = {}
    for row in solar_rows:
        minute = row["raw_minute"]
        bucket = minute[:14] + f"{(int(minute[14:16]) // stride) * stride:02d}"
        group = bins.setdefault(
            bucket,
            {
                "solar_sum": 0.0,
                "solar_n": 0,
                "soc_sum": 0.0,
                "soc_n": 0,
                "charge_sum": 0.0,
                "charge_n": 0,
                "observed_boxes": 0,
            },
        )
        if row["solar_kw"] is not None:
            group["solar_sum"] += row["solar_kw"]
            group["solar_n"] += 1
        if row["battery_soc_pct"] is not None:
            group["soc_sum"] += row["battery_soc_pct"]
            group["soc_n"] += 1
        if minute in charging:
            group["charge_sum"] += charging[minute][0]
            group["charge_n"] += 1
            group["observed_boxes"] = max(group["observed_boxes"], charging[minute][1])
    return {
        "hours": hours,
        "bin_minutes": stride,
        "points": [
            {
                "raw_time": key,
                "site_time": site_time(key, config),
                "solar_kw": val["solar_sum"] / val["solar_n"] if val["solar_n"] else None,
                "battery_soc_pct": val["soc_sum"] / val["soc_n"] if val["soc_n"] else None,
                "observed_charging_kw": val["charge_sum"] / val["charge_n"]
                if val["charge_n"]
                else None,
                "observed_wallboxes": val["observed_boxes"],
                "solar_minutes": val["solar_n"],
                "charging_minutes": val["charge_n"],
            }
            for key, val in sorted(bins.items())
        ],
    }
