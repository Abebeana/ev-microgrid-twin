"""CSV columns, types, and keys shared by ingestion and readers."""

SCHEMA_VERSION = "8"
TABLES = {
    "microgrid_minute": {
        "raw_minute": str,
        "sample_count": int,
        "solar_kw": float,
        "solar_samples": int,
        "battery_soc_pct": float,
        "battery_temp_c": float,
        "p_sum_kw": float,
        "soc_bad_samples": int,
        "solar_bad_samples": int,
    },
    "charger_minute": {
        "raw_minute": str,
        "wallbox_id": str,
        "power_kw": float,
        "sample_count": int,
        "last_raw_timestamp": str,
    },
    "wallbox": {"id": str, "vendor": str, "model": str, "firmware": str},
    "connector_event": {
        "connector_pk": int,
        "wallbox_id": str,
        "raw_timestamp": str,
        "status": str,
        "error_code": str,
    },
    "charging_session": {
        "transaction_id": int,
        "wallbox_id": str,
        "start_raw": str,
        "stop_raw": str,
        "start_meter_raw": float,
        "stop_meter_raw": float,
        "stop_reason": str,
    },
    "quality_check": {"code": str, "count": int, "detail": str},
}
KEYS = {
    "microgrid_minute": ("raw_minute",),
    "charger_minute": ("raw_minute", "wallbox_id"),
    "wallbox": ("id",),
    "connector_event": ("raw_timestamp", "connector_pk", "status"),
    "charging_session": ("transaction_id",),
    "quality_check": ("code",),
}
