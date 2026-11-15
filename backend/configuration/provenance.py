"""Fingerprints for settings that affect processed measurements."""

import hashlib
import json


def ingestion_fingerprint(config) -> str:
    fields = (
        "source_timestamp_timezone",
        "solar_validation_max_kw",
        "charger_validation_max_kw",
        "battery_temperature_min_c",
        "battery_temperature_max_c",
    )
    values = {key: getattr(config, key) for key in fields}
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
