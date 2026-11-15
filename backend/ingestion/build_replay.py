"""Build validated CSV tables and atomically publish their JSON manifest."""

import json
from pathlib import Path

from backend.configuration.dataset import SOURCE_CONTRACT, derived_path, raw_path
from backend.configuration.provenance import ingestion_fingerprint
from backend.configuration.site import load_site_config
from backend.ingestion.charging import charging_sessions, inventory, power_readings, status_events
from backend.ingestion.microgrid import aggregate_microgrid
from backend.ingestion.replay_schema import SCHEMA_VERSION
from backend.ingestion.split_json_reader import SplitJsonReader
from backend.ingestion.value_conversion import sha256
from backend.storage.atomic import file_lock
from backend.storage.replay_writer import ReplayWriter


def build_replay(source_path: Path | None = None, output_path: Path | None = None) -> dict:
    source_path = source_path or raw_path()
    output_path = output_path or derived_path()
    if source_path.resolve() != raw_path().resolve():
        raise ValueError("SOFIE source path differs from the pinned JSON")
    if output_path.resolve() == source_path.resolve() or output_path.is_file():
        raise ValueError("Processed output must be a directory separate from the source JSON")
    config = load_site_config()
    with file_lock(output_path / ".build.lock"):
        source_hash = sha256(source_path)
        if source_hash != SOURCE_CONTRACT["sha256"]:
            raise ValueError("SOFIE source SHA-256 differs from the pinned JSON")
        target = ReplayWriter(output_path)
        try:
            with SplitJsonReader(source_path) as source:
                source.indices("scn_values", ("timestamp", "SCN_L1", "SCN_L2", "SCN_L3"))
                boxes, connectors = inventory(source)
                box_count = target.table("wallbox", boxes)
                microgrid, quality = aggregate_microgrid(source, config)
                microgrid_count = target.table("microgrid_minute", microgrid)
                del microgrid
                power, invalid_power = power_readings(source, connectors, config)
                charger_count = target.table("charger_minute", power)
                del power
                events, conflicting_events = status_events(source, connectors)
                target.table("connector_event", events)
                sessions, session_quality = charging_sessions(source, connectors)
                target.table("charging_session", sessions)
            checks = [
                (
                    "conflicting_status_events",
                    conflicting_events,
                    "Concurrent status error codes preserved as a sorted, pipe-separated set",
                ),
                (
                    "invalid_charger_power",
                    invalid_power,
                    f"Power.Active.Import outside 0–{config.charger_validation_max_kw:g} kW or nonnumeric",
                ),
                (
                    "invalid_solar_power",
                    quality["bad_solar"],
                    f"p_actual outside 0–{config.solar_validation_max_kw:g} kW or nonnumeric",
                ),
                ("invalid_battery_soc", quality["bad_soc"], "bat_soc outside 0–100% or nonnumeric"),
                (
                    "missing_solar_samples",
                    quality["missing_solar"],
                    "Null or JSON 'None' is unknown; nighttime gaps are not converted to zero",
                ),
                (
                    "open_sessions",
                    sum(row[3] is None for row in sessions),
                    "Starts with no matching stop in this file",
                ),
                (
                    "duplicate_stop_ids",
                    session_quality["duplicate_stops"],
                    "Latest stop timestamp retained per transaction ID",
                ),
                (
                    "unmatched_stop_ids",
                    session_quality["unmatched_stops"],
                    "Stops without a start in this JSON period; no session is invented",
                ),
            ]
            target.table("quality_check", checks)
            metadata = {
                "schema_version": SCHEMA_VERSION,
                "source_sha256": source_hash,
                "ingestion_config_sha256": ingestion_fingerprint(config),
                "source_filename": source_path.name,
                "source_timezone_interpretation": config.source_timestamp_timezone,
                "source_timezone_evidence": config.source_timezone_evidence,
                "site_timezone": config.site_timezone,
                "first_raw": quality["first_raw"],
                "last_raw": quality["last_raw"],
                "wallbox_count": box_count,
                "microgrid_minutes": microgrid_count,
                "charger_minutes": charger_count,
            }
            if sha256(source_path) != source_hash:
                raise ValueError("Source changed during ingestion; refusing to publish")
            target.publish(metadata)
            return {**metadata, "quality": {code: count for code, count, _ in checks}}
        finally:
            target.close()


if __name__ == "__main__":
    print(json.dumps(build_replay(), indent=2))
