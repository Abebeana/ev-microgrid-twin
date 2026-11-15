"""Regression checks for crash safety, provenance, integrity, and coverage."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from backend.configuration.dataset import derived_path
from backend.ingestion.build_replay import build_replay
from backend.ingestion.replay_schema import TABLES
from backend.optimization.contracts import ScenarioInput
from backend.optimization.inputs import scenario_inputs
from backend.storage import atomic
from backend.storage.replay_reader import read_replay
from backend.storage.replay_writer import ReplayWriter
from backend.telemetry.repository import replay_store


def republish(store, change):
    writer = ReplayWriter(derived_path())
    try:
        for name, schema in TABLES.items():
            rows = change(name, store.table(name))
            writer.table(name, (tuple(row[key] for key in schema) for row in rows))
        writer.publish(store.metadata)
    finally:
        writer.close()


def test_csv_nulls_types_and_file_inventory(fixture_site):
    store = read_replay(derived_path())
    row = store.table("microgrid_minute")[0]
    assert row["solar_kw"] is None
    assert row["solar_samples"] == 0
    assert isinstance(row["battery_soc_pct"], float)
    assert {path.suffix for path in store.directory.iterdir()} == {".csv"}
    assert len(list(store.directory.iterdir())) == len(TABLES)


def test_failed_build_preserves_published_generation(fixture_site):
    manifest = derived_path() / "manifest.json"
    before = manifest.read_bytes()
    generations = set((derived_path() / "generations").iterdir())
    with patch("backend.ingestion.build_replay.power_readings", side_effect=ValueError("failure")):
        with pytest.raises(ValueError, match="failure"):
            build_replay()
    assert manifest.read_bytes() == before
    assert set((derived_path() / "generations").iterdir()) == generations
    assert read_replay(derived_path()).table("wallbox")


def test_generation_switch_preserves_existing_readers(fixture_site):
    old = read_replay(derived_path())
    republish(old, lambda name, rows: rows)
    current = read_replay(derived_path())
    assert current.directory != old.directory
    assert current.table("microgrid_minute") == old.table("microgrid_minute")


def test_corruption_is_detected_after_index_is_cached(fixture_site):
    store = read_replay(derived_path())
    assert store.latest("microgrid_minute", "2025-10-26 00:31")
    path = store.directory / "microgrid_minute.csv"
    path.write_text(path.read_text().replace("5.0", "9.0"))
    with pytest.raises(HTTPException, match="integrity check failed"):
        with replay_store() as reader:
            reader.latest("microgrid_minute", "2025-10-26 00:31")


def test_configuration_drift_requires_rebuild(fixture_site, monkeypatch, tmp_path):
    config_path = tmp_path / "site.json"
    config = json.loads(config_path.read_text())
    config["solar_validation_max_kw"] = 1
    config_path.write_text(json.dumps(config))
    with pytest.raises(HTTPException, match="Ingestion settings changed"):
        with replay_store():
            pass


def test_partial_fleet_does_not_count_as_covered(fixture_site):
    store = read_replay(derived_path())
    republish(
        store,
        lambda name, rows: (
            [row for row in rows if row["wallbox_id"] != "WB3"]
            if name == "charger_minute"
            else rows
        ),
    )
    with pytest.raises(HTTPException, match="Insufficient measured"):
        scenario_inputs(ScenarioInput(start="raw:2025-10-26T00:30", hours=1))
    # A declared outage explicitly removes that charger from required coverage.
    slots, _ = scenario_inputs(
        ScenarioInput(start="raw:2025-10-26T00:30", hours=1, outage_wallbox_id="WB3")
    )
    assert slots[0]["observed_charging_kw"] == 12


def test_failed_atomic_replace_keeps_original_and_removes_temporary(tmp_path):
    path = tmp_path / "state.json"
    atomic.write_json(path, {"version": 1})
    with patch("backend.storage.atomic.os.replace", side_effect=OSError("disk failure")):
        with pytest.raises(OSError, match="disk failure"):
            atomic.write_json(path, {"version": 2})
    assert json.loads(path.read_text()) == {"version": 1}
    assert list(tmp_path.iterdir()) == [path]


def test_incomplete_generation_cannot_be_published(tmp_path):
    writer = ReplayWriter(tmp_path / "replay")
    try:
        writer.table("wallbox", [("WB1", None, None, None)])
        with pytest.raises(ValueError, match="incomplete"):
            writer.publish({})
    finally:
        writer.close()
    assert not (tmp_path / "replay/manifest.json").exists()


def test_duplicate_keys_are_not_silently_overwritten(tmp_path):
    writer = ReplayWriter(tmp_path / "replay")
    try:
        with pytest.raises(ValueError, match="Duplicate wallbox key"):
            writer.table("wallbox", [("WB1", None, None, None)] * 2)
    finally:
        writer.close()


def test_sqlite_is_confined_to_operator_state():
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*.py"):
        if "operations" in path.parts or "tests" in path.parts:
            continue
        assert "import sqlite3" not in path.read_text(), path


def test_sync_failure_after_publish_does_not_delete_active_generation(fixture_site):
    store = read_replay(derived_path())
    writer = ReplayWriter(derived_path())
    for name, schema in TABLES.items():
        writer.table(name, (tuple(row[key] for key in schema) for row in store.table(name)))
    with patch("backend.storage.atomic.sync_directory", side_effect=OSError("sync failed")):
        with pytest.raises(OSError, match="sync failed"):
            writer.publish(store.metadata)
    writer.close()
    current = read_replay(derived_path())
    assert current.directory == writer.directory
    assert current.table("microgrid_minute") == store.table("microgrid_minute")
