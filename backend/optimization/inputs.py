"""Validate measurement coverage and build observed dispatch intervals."""

from datetime import timedelta

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.optimization.contracts import ScenarioInput
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time


def scenario_inputs(request: ScenarioInput) -> tuple[list[dict], float]:
    config = load_site_config()
    start = source_time(request.start, config)
    step = config.optimizer_step_minutes
    if start.minute % step or start.second or start.microsecond:
        raise HTTPException(422, f"Scenario start must align to a {step}-minute boundary")
    end = start + timedelta(hours=request.hours)
    with replay_store() as store:
        wallboxes = {row["id"] for row in store.table("wallbox")}
        if request.outage_wallbox_id and request.outage_wallbox_id not in wallboxes:
            raise HTTPException(422, "Unknown wallbox in outage scenario")
        required_boxes = len(wallboxes - {request.outage_wallbox_id})
        rows = store.between(
            "microgrid_minute", raw_string(start), raw_string(end), end_inclusive=False
        )
        chargers = store.between(
            "charger_minute", raw_string(start), raw_string(end), end_inclusive=False
        )
    by_minute: dict[str, dict] = {}
    for row in rows:
        by_minute[row["raw_minute"]] = {
            "solar": row["solar_kw"],
            "soc": row["battery_soc_pct"],
            "charging": 0.0,
            "charger_count": 0,
        }
    for row in chargers:
        if row["raw_minute"] in by_minute and row["wallbox_id"] != request.outage_wallbox_id:
            by_minute[row["raw_minute"]]["charging"] += row["power_kw"]
            by_minute[row["raw_minute"]]["charger_count"] += 1
    initial = by_minute.get(raw_string(start), {}).get("soc")
    if initial is None:
        raise HTTPException(422, "Battery state of charge is unavailable at the scenario start")
    slots = []
    for index in range(request.hours * 60 // step):
        slot = start + timedelta(minutes=index * step)
        subset = [by_minute.get(raw_string(slot + timedelta(minutes=m))) for m in range(step)]
        paired = [
            v
            for v in subset
            if v and v["solar"] is not None and v["charger_count"] == required_boxes
        ]
        solar = [v["solar"] for v in paired]
        charging = [v["charging"] for v in paired]
        coverage = min(len(solar), len(charging)) / step * 100
        if coverage < config.optimizer_min_coverage_pct:
            raise HTTPException(
                422,
                f"Insufficient measured PV/charger coverage at {raw_string(slot)} ({coverage:.0f}%); required {config.optimizer_min_coverage_pct:g}%",
            )
        slots.append(
            {
                "raw_time": raw_string(slot),
                "site_time": site_time(raw_string(slot), config),
                "solar_kw": sum(solar) / len(solar) * request.solar_multiplier,
                "observed_charging_kw": sum(charging) / len(charging) * request.charging_multiplier,
                "coverage_pct": coverage,
                "minimum_reporting_wallboxes": min(
                    (v["charger_count"] for v in subset if v), default=0
                ),
            }
        )
    return slots, initial
