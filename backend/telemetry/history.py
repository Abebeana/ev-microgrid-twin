"""Site snapshots, aggregate trends, and measurement quality."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.ingestion.replay_schema import SCHEMA_VERSION
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time
from backend.telemetry.trends import trend as trend


def site() -> dict:
    config = load_site_config()
    with replay_store() as store:
        boxes = list(store.table("wallbox"))
        meta = dict(store.metadata)
    if meta["schema_version"] != SCHEMA_VERSION:
        raise HTTPException(503, "Replay schema changed; rebuild the CSV files")
    if meta["source_timezone_interpretation"] != config.source_timestamp_timezone:
        raise HTTPException(503, "Timezone configuration changed; rebuild the replay CSV files")
    return {
        "config": config.model_dump(),
        "wallboxes": boxes,
        "metadata": meta,
        "default_raw": raw_string(source_time(config.default_replay_at, config)),
        "mode": "historical_replay",
        "live_connected": False,
    }


def snapshot(at: str | None = None) -> dict:
    config = load_site_config()
    moment = source_time(at, config)
    minute = raw_string(moment)
    with replay_store() as store:
        meta = dict(store.metadata)
        if minute < meta["first_raw"][:16] or minute > meta["last_raw"][:16]:
            raise HTTPException(422, "Replay time is outside the SOFIE observation window")
        row = store.latest("microgrid_minute", minute)
        boxes = []
        for box in store.table("wallbox"):
            power = store.latest("charger_minute", minute, wallbox_id=box["id"])
            event = store.latest(
                "connector_event",
                minute + ":59.999999",
                field="raw_timestamp",
                wallbox_id=box["id"],
            )
            power_fresh = bool(
                power
                and datetime.fromisoformat(power["raw_minute"])
                >= moment - timedelta(minutes=config.charger_stale_minutes)
            )
            event_fresh = bool(
                event
                and datetime.fromisoformat(event["raw_timestamp"])
                >= moment - timedelta(minutes=config.charger_stale_minutes)
            )
            boxes.append(
                {
                    "id": box["id"],
                    "vendor": box["vendor"],
                    "model": box["model"],
                    "firmware": box["firmware"],
                    "power_kw": power["power_kw"] if power_fresh else None,
                    "power_sample_count": power["sample_count"] if power_fresh else 0,
                    "power_raw_time": power["last_raw_timestamp"] if power_fresh else None,
                    "power_site_time": site_time(power["last_raw_timestamp"], config)
                    if power_fresh
                    else None,
                    "status": event["status"] if event else "Unknown",
                    "status_stale": not event_fresh,
                    "error_code": event["error_code"] if event else None,
                    "status_site_time": site_time(event["raw_timestamp"], config)
                    if event
                    else None,
                }
            )
        active_sessions = sum(
            row["start_raw"] <= minute + ":59"
            and row["stop_raw"] is not None
            and row["stop_raw"] > minute
            for row in store.table("charging_session")
        )
    observed = [box["power_kw"] for box in boxes if box["power_kw"] is not None]
    solar = row["solar_kw"] if row and row["raw_minute"] == minute else None
    return {
        "mode": "historical_replay",
        "raw_time": minute,
        "site_time": site_time(minute, config),
        "source_timezone_interpretation": config.source_timestamp_timezone,
        "solar_kw": solar,
        "solar_samples": row["solar_samples"] if row and row["raw_minute"] == minute else 0,
        "battery_soc_pct": row["battery_soc_pct"] if row and row["raw_minute"] == minute else None,
        "battery_temp_c": row["battery_temp_c"] if row and row["raw_minute"] == minute else None,
        "p_sum_kw": row["p_sum_kw"] if row and row["raw_minute"] == minute else None,
        "observed_charging_kw": sum(observed) if observed else None,
        "observed_wallboxes": len(observed),
        "active_sessions": active_sessions,
        "total_wallboxes": len(boxes),
        "wallboxes": boxes,
        "unavailable": {
            "grid_import_kw": "Islanded site; no grid connection",
            "tariff": "No tariff source",
            "weather": "No weather source",
            "forecast": "No forecast source",
        },
    }


def quality() -> dict:
    with replay_store() as store:
        checks = list(store.table("quality_check"))
        meta = dict(store.metadata)
        rows = store.table("microgrid_minute")
        period = {
            "minutes": len(rows),
            "solar_minutes": sum(r["solar_samples"] > 0 for r in rows),
            "bad_soc": sum(r["soc_bad_samples"] for r in rows),
        }
    return {"checks": checks, "metadata": meta, "minutes": period}
