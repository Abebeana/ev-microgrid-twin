"""Historical charger faults and battery threshold events."""

from __future__ import annotations

from datetime import timedelta

from backend.configuration.site import load_site_config
from backend.telemetry.repository import replay_store
from backend.telemetry.timestamps import raw_string, site_time, source_time


def alarms(at: str | None) -> list[dict]:
    config = load_site_config()
    moment = source_time(at, config)
    start = (moment - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    end = moment.strftime("%Y-%m-%d %H:%M:%S")
    with replay_store() as store:
        events = [
            row
            for row in reversed(store.between("connector_event", start, end, field="raw_timestamp"))
            if row["status"] == "Faulted" or row["error_code"] not in (None, "NoError")
        ][:100]
        battery_rows = store.between(
            "microgrid_minute", raw_string(moment - timedelta(hours=24, minutes=1)), end[:16]
        )
    result = [
        {
            "id": f"{r['wallbox_id']}:{r['raw_timestamp']}",
            "asset_id": r["wallbox_id"],
            "severity": "warning",
            "message": f"{r['status']} · {r['error_code'] or 'status event'}",
            "raw_time": r["raw_timestamp"],
            "site_time": site_time(r["raw_timestamp"], config),
            "provenance": "connector_status",
        }
        for r in events
    ]
    previous_low = previous_hot = None
    for row in battery_rows:
        low = (
            row["battery_soc_pct"] is not None
            and row["battery_soc_pct"] < config.battery_low_soc_alarm_pct
        )
        hot = (
            row["battery_temp_c"] is not None
            and row["battery_temp_c"] > config.battery_high_temp_alarm_c
        )
        if row["raw_minute"] >= start[:16]:
            for triggered, previous, code, field, threshold in (
                (
                    low,
                    previous_low,
                    "LOW_SOC",
                    "battery_soc_pct",
                    config.battery_low_soc_alarm_pct,
                ),
                (
                    hot,
                    previous_hot,
                    "BAT_TEMP",
                    "battery_temp_c",
                    config.battery_high_temp_alarm_c,
                ),
            ):
                if triggered and previous is False:
                    result.append(
                        {
                            "id": f"{code}:{row['raw_minute']}",
                            "asset_id": "BESS",
                            "severity": "warning",
                            "message": f"{field} crossed threshold: {row[field]:.1f} (limit {threshold:g})",
                            "raw_time": row["raw_minute"],
                            "site_time": site_time(row["raw_minute"], config),
                            "provenance": "logging",
                        }
                    )
        previous_low, previous_hot = low, hot
    return sorted(result, key=lambda alarm: alarm["raw_time"], reverse=True)
