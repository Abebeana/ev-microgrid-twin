"""Small source export shared by storage and application integration tests."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from backend.ingestion.build_replay import build_replay


@pytest.fixture
def fixture_site(tmp_path, monkeypatch):
    source = tmp_path / "raw.json"
    derived = tmp_path / "replay"
    config = json.loads((Path(__file__).resolve().parents[2] / "config/site.json").read_text())
    config["default_replay_at"] = "2025-10-26T00:30:00+00:00"
    config_path = tmp_path / "site.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setenv("TWIN_SITE_CONFIG", str(config_path))
    monkeypatch.setenv("TWIN_RAW_JSON", str(source))
    monkeypatch.setenv("TWIN_REPLAY_DIR", str(derived))
    monkeypatch.setenv("TWIN_OPERATIONS_DB", str(tmp_path / "operations.db"))
    tables = {
        "logging": (["timestamp", "p_actual", "bat_soc", "bat_temp", "P_sum"], []),
        "scn_values": (["timestamp", "SCN_L1", "SCN_L2", "SCN_L3"], []),
        "charge_box": (
            [
                "charge_box_id",
                "charge_point_vendor",
                "charge_point_model",
                "fw_version",
            ],
            [],
        ),
        "connector": (["connector_pk", "charge_box_id", "connector_id"], []),
        "transaction_start": (
            ["transaction_pk", "connector_pk", "start_timestamp", "start_value"],
            [],
        ),
        "transaction_stop": (
            ["transaction_pk", "stop_timestamp", "stop_value", "stop_reason"],
            [],
        ),
        "connector_meter_value": (
            ["connector_pk", "value_timestamp", "value", "measurand", "unit"],
            [],
        ),
        "connector_status": (
            ["connector_pk", "status_timestamp", "status", "error_code"],
            [],
        ),
    }
    for index in range(3):
        tables["charge_box"][1].append([f"WB{index + 1}", "Alfen", "Test", "1"])
        tables["connector"][1].append([index + 1, f"WB{index + 1}", 1])
        tables["connector_status"][1].append(
            [
                index + 1,
                "2025-10-26 00:30:00",
                "Faulted" if index == 1 else "Charging",
                "UnderVoltage" if index == 1 else "NoError",
            ]
        )
    start = datetime(2025, 10, 26, 0, 30)
    for index in range(60):
        stamp = (start + timedelta(minutes=index)).strftime("%Y-%m-%d %H:%M:%S")
        tables["logging"][1].append([stamp, "None" if index == 0 else 5000, 80, 250, 10])
        for box in range(3):
            tables["connector_meter_value"][1].append(
                [box + 1, stamp, "6000", "Power.Active.Import", "W"]
            )
    tables["transaction_start"][1].append([1, 1, "2025-10-26 00:30:00", "100000"])
    tables["transaction_stop"][1].append([1, "2025-10-26 01:10:00", "104000", "Local"])
    tables["transaction_stop"][1].append([2, "2025-10-26 01:15:00", "105000", "Local"])
    source.write_text(
        json.dumps(
            {
                name: {
                    "index": list(range(len(rows))),
                    "columns": columns,
                    "data": rows,
                }
                for name, (columns, rows) in tables.items()
            },
            indent=2,
        )
    )
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    from backend.configuration import dataset as settings

    monkeypatch.setattr(settings, "DEFAULT_RAW", source)
    monkeypatch.setitem(settings.SOURCE_CONTRACT, "sha256", before)
    report = build_replay(source, derived)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert report["wallbox_count"] == 3
    assert report["quality"]["unmatched_stop_ids"] == 1
    assert report["quality"]["missing_solar_samples"] == 1
    return report
