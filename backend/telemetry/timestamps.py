"""Explicit conversion between recorded, timezone-aware, and site clocks."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from backend.configuration.site import SiteConfig


def source_time(value: str | None, config: SiteConfig) -> datetime:
    if value is None:
        value = config.default_replay_at
    if value.startswith("raw:"):
        try:
            raw = datetime.fromisoformat(value[4:])
        except ValueError as error:
            raise HTTPException(422, "Invalid recorded source timestamp") from error
        if raw.tzinfo is not None:
            raise HTTPException(422, "raw: timestamps must not include an offset")
        _check_unambiguous(raw, config)
        return raw
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise HTTPException(422, "Use an ISO timestamp with a timezone offset") from error
    if parsed.tzinfo is None:
        raise HTTPException(422, "Replay timestamps require an explicit timezone offset")
    raw = parsed.astimezone(ZoneInfo(config.source_timestamp_timezone)).replace(tzinfo=None)
    _check_unambiguous(raw, config)
    return raw


def _check_unambiguous(raw: datetime, config: SiteConfig) -> None:
    zone = ZoneInfo(config.source_timestamp_timezone)
    if raw.replace(tzinfo=zone, fold=0).utcoffset() != raw.replace(tzinfo=zone, fold=1).utcoffset():
        raise HTTPException(
            422,
            "Source clock repeats this local time; the unzoned file cannot distinguish its occurrence",
        )


def raw_string(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M")


def site_time(raw: str | None, config: SiteConfig) -> str | None:
    if raw is None:
        return None
    source = datetime.fromisoformat(raw)
    _check_unambiguous(source, config)
    return (
        source.replace(tzinfo=ZoneInfo(config.source_timestamp_timezone))
        .astimezone(ZoneInfo(config.site_timezone))
        .isoformat()
    )
