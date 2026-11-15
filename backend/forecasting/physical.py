"""Clear-sky PV forecast with intervals learned from earlier recorded minutes."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import cos, pi, sin
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from backend.configuration.site import SiteConfig, load_site_config
from backend.forecasting import clearsky, conformal
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time

HORIZONS = (15, 30, 45, 60)


def forecast(at: str | None = None) -> dict:
    config = load_site_config()
    origin = source_time(at, config)
    origin_raw = raw_string(origin)
    with replay_store() as store:
        metadata = dict(store.metadata)
        if origin_raw < metadata["first_raw"][:16] or origin_raw > metadata["last_raw"][:16]:
            raise HTTPException(422, "Forecast origin is outside the SOFIE observation window")
        history = _history(store, origin, config)
        recorded = {
            row["raw_minute"]: row["solar_kw"]
            for row in store.between(
                "microgrid_minute",
                origin_raw,
                raw_string(origin + timedelta(minutes=HORIZONS[-1])),
            )
        }
    moments = [_site_clock(origin + timedelta(minutes=minutes), config) for minutes in HORIZONS]
    shape = clearsky.pvwatts_kw(moments, config, nameplate_kw=1)
    trained = conformal.intervals(
        [_features(sample["shape_kw"], sample["moment"]) for sample in history],
        [sample["measured_kw"] for sample in history],
        [_features(value, moment) for value, moment in zip(shape, moments)],
    )
    rows = []
    for index, minutes in enumerate(HORIZONS):
        moment = origin + timedelta(minutes=minutes)
        point = _point(trained, index, shape[index], config.pv_nameplate_kw)
        rows.append(
            {
                "horizon_minutes": minutes,
                "raw_time": raw_string(moment),
                "site_time": site_time(raw_string(moment), config),
                "clearsky_kw": point,
                "lower_kw": None if not trained["calibrated"] else trained["lower_kw"][index],
                "upper_kw": None if not trained["calibrated"] else trained["upper_kw"][index],
                "recorded_kw": recorded.get(raw_string(moment)),
            }
        )
    return {
        "model": "pvlib Ineichen clear-sky and PVWatts, MAPIE split conformal",
        "calibrated": trained["calibrated"],
        "confidence_level": 0.8 if trained["calibrated"] else None,
        "scale_on_one_kw_array": trained["scale"],
        "training_samples": len(history),
        "nameplate_clip_kw": config.pv_nameplate_kw,
        "location_assumption": config.location_assumption,
        "pv_nameplate_note": config.pv_nameplate_note,
        "origin_raw": origin_raw,
        "origin_site_time": site_time(origin_raw, config),
        "source_sha256": metadata["source_sha256"],
        "rows": rows,
    }


def _history(store, origin: datetime, config: SiteConfig) -> list[dict]:
    start = raw_string(origin - timedelta(days=14))
    rows = []
    for row in store.between("microgrid_minute", start, raw_string(origin), end_inclusive=False):
        minute = row["raw_minute"]
        if not minute.endswith((":00", ":30")) or row["solar_kw"] is None:
            continue
        rows.append(
            {
                "moment": _site_clock(datetime.fromisoformat(minute), config),
                "measured_kw": float(row["solar_kw"]),
            }
        )
    if not rows:
        return []
    shape = clearsky.pvwatts_kw([row["moment"] for row in rows], config, nameplate_kw=1)
    for row, value in zip(rows, shape):
        row["shape_kw"] = value
    return rows


def _site_clock(moment: datetime, config: SiteConfig) -> datetime:
    naive = moment.replace(tzinfo=None)
    return naive.replace(tzinfo=ZoneInfo(config.source_timestamp_timezone)).astimezone(
        ZoneInfo(config.site_timezone)
    )


def _features(shape_kw: float, moment: datetime) -> list[float]:
    hour = moment.hour + moment.minute / 60
    return [shape_kw, sin(2 * pi * hour / 24), cos(2 * pi * hour / 24)]


def _point(trained: dict, index: int, shape_kw: float, ceiling_kw: float) -> float:
    if trained["calibrated"]:
        value = trained["point_kw"][index]
    else:
        value = shape_kw * ceiling_kw
    return round(min(max(value, 0), ceiling_kw), 3)
