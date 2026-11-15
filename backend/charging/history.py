"""Charger trends and reconstructed charging sessions."""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time


def sessions(at: str | None, wallbox_id: str | None = None, limit: int = 50) -> list[dict]:
    config = load_site_config()
    minute = raw_string(source_time(at, config))
    if limit < 1 or limit > 200:
        raise HTTPException(422, "limit must be 1–200")
    with replay_store() as store:
        rows = sorted(
            (
                row
                for row in store.table("charging_session")
                if row["start_raw"] <= minute + ":59"
                and (wallbox_id is None or row["wallbox_id"] == wallbox_id)
            ),
            key=lambda row: row["start_raw"],
            reverse=True,
        )[:limit]
    return [
        {
            **dict(row),
            "start_site_time": site_time(row["start_raw"], config),
            "stop_site_time": site_time(row["stop_raw"], config),
            "meter_delta_raw": row["stop_meter_raw"] - row["start_meter_raw"]
            if row["stop_meter_raw"] is not None
            and row["start_meter_raw"] is not None
            and row["stop_meter_raw"] >= row["start_meter_raw"]
            else None,
        }
        for row in rows
    ]


def charger_trend(wallbox_id: str, at: str | None, hours: int = 24) -> list[dict]:
    if hours not in (6, 24, 72):
        raise HTTPException(422, "hours must be 6, 24, or 72")
    config = load_site_config()
    moment = source_time(at, config)
    with replay_store() as store:
        if not any(row["id"] == wallbox_id for row in store.table("wallbox")):
            raise HTTPException(404, "Unknown wallbox")
        rows = store.between(
            "charger_minute",
            raw_string(moment - timedelta(hours=hours)),
            raw_string(moment),
            wallbox_id=wallbox_id,
        )
    stride = 5 if hours == 6 else 15 if hours == 24 else 30
    bins: dict[str, list[float]] = {}
    for row in rows:
        minute = row["raw_minute"]
        bucket = minute[:14] + f"{(int(minute[14:16]) // stride) * stride:02d}"
        bins.setdefault(bucket, []).append(row["power_kw"])
    return [
        {
            "raw_time": key,
            "site_time": site_time(key, config),
            "power_kw": sum(values) / len(values),
            "observed_minutes": len(values),
        }
        for key, values in sorted(bins.items())
    ]
