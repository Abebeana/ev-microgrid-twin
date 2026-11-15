"""Persistence forecasts with paired historical error estimates."""

from __future__ import annotations

from datetime import timedelta
from math import ceil

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time


def _error_summary(errors: list[float]) -> dict:
    if not errors:
        return {"samples": 0, "mae_kw": None, "p80_absolute_error_kw": None}
    ordered = sorted(errors)
    return {
        "samples": len(errors),
        "mae_kw": round(sum(errors) / len(errors), 3),
        "p80_absolute_error_kw": round(ordered[ceil(0.8 * len(ordered)) - 1], 3)
        if len(errors) >= 4
        else None,
    }


def baseline(at: str | None = None) -> dict:
    config = load_site_config()
    moment = source_time(at, config)
    raw = raw_string(moment)
    window_start = raw_string(moment - timedelta(hours=7))
    window_end = raw_string(moment + timedelta(hours=1))
    with replay_store() as store:
        metadata = dict(store.metadata)
        if raw < metadata["first_raw"][:16] or raw > metadata["last_raw"][:16]:
            raise HTTPException(422, "Forecast origin is outside the SOFIE observation window")
        wallboxes = len(store.table("wallbox"))
        solar = {
            row["raw_minute"]: row["solar_kw"]
            for row in store.between("microgrid_minute", window_start, window_end)
        }
        charging = {
            row["raw_minute"]: row["power_kw"] if row["boxes"] == wallboxes else None
            for row in store.charging_totals(window_start, window_end)
        }

    def value(series: dict, time) -> float | None:
        return series.get(raw_string(time))

    current_solar = value(solar, moment)
    current_ev = value(charging, moment)
    rows = []
    for horizon in (15, 30, 45, 60):
        target = moment + timedelta(minutes=horizon)
        solar_errors = []
        ev_errors = []
        for offset in range(1, 25):
            past = moment - timedelta(minutes=15 * offset)
            future = past + timedelta(minutes=horizon)
            if future > moment:
                continue
            for series, errors in ((solar, solar_errors), (charging, ev_errors)):
                before, after = value(series, past), value(series, future)
                if before is not None and after is not None:
                    errors.append(abs(after - before))
        rows.append(
            {
                "horizon_minutes": horizon,
                "raw_time": raw_string(target),
                "site_time": site_time(raw_string(target), config),
                "solar": {
                    "predicted_kw": current_solar,
                    "recorded_kw": value(solar, target),
                    "validation": _error_summary(solar_errors),
                },
                "observed_ev": {
                    "predicted_kw": current_ev,
                    "recorded_kw": value(charging, target),
                    "validation": _error_summary(ev_errors),
                },
            }
        )
    return {
        "model": "persistence baseline",
        "mode": "retrospective_baseline",
        "origin_raw": raw,
        "origin_site_time": site_time(raw, config),
        "source_sha256": metadata["source_sha256"],
        "wallboxes_required": wallboxes,
        "rows": rows,
        "scope": "PV and fully observed EV wallboxes only; a missing source minute has no prediction",
        "uncertainty_note": "The band is the 80th percentile of absolute errors from up to 24 prior 15-minute origins. It is descriptive, not a calibrated prediction interval.",
    }
