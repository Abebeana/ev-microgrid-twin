"""Critical data, time, advisory, and operator workflows on a small source fixture."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

import pytest

from backend.alarms import events
from backend.api.routes.alarms import AcknowledgementRequest, acknowledge
from backend.api.routes.audit import audit
from backend.api.routes.reinforcement_learning import rl_experiment
from backend.api.routes.scenarios import SaveScenarioRequest, save_scenario
from backend.api.routes.topology import get_graph
from backend.configuration.site import load_site_config
from backend.forecasting import persistence as forecast
from backend.ingestion.build_replay import build_replay
from backend.operations import database as operation_database
from backend.operations import scenario_runs
from backend.optimization import dispatch as analysis
from backend.streaming.replay_publisher import make_frame
from backend.streaming.state import TelemetryStream
from backend.telemetry import history as replay
from backend.telemetry import repository, timestamps
from backend.tests.graph_double import GraphDouble


def test_pipeline_units_nulls_dynamic_assets_and_dst(fixture_site, tmp_path, monkeypatch):
    observed = replay.snapshot("2025-10-26T00:31:00+00:00")
    assert observed["solar_kw"] == 5.0
    assert observed["observed_charging_kw"] == 18.0
    assert observed["battery_soc_pct"] == 80
    assert observed["battery_temp_c"] == 25
    assert observed["total_wallboxes"] == 3
    assert replay.snapshot("2025-10-26T00:30:00+00:00")["solar_kw"] is None
    assert timestamps.site_time("2025-10-26 00:30", load_site_config()).endswith("+02:00")
    assert timestamps.site_time("2025-10-26 01:30", load_site_config()).endswith("+01:00")
    with pytest.raises(Exception):
        timestamps.source_time("2025-10-26T00:30:00", load_site_config())
    config_path = tmp_path / "site.json"
    config = json.loads(config_path.read_text())
    config["assets"].insert(
        1,
        {"id": "PV2", "name": "Second PV unit", "kind": "solar", "connected_to": "BUS"},
    )
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr("backend.api.routes.topology.graph_store", GraphDouble())
    graph = get_graph("2025-10-26T00:31:00+00:00")
    assert sum(node["kind"] == "solar" for node in graph["nodes"]) == 2
    assert all(node["value"] is None for node in graph["nodes"] if node["kind"] == "solar")
    assert sum(node["kind"] == "charger" for node in graph["nodes"]) == 3
    assert graph["store"] == "test-double"
    assert any(edge["relation"] == "CONNECTED_TO" for edge in graph["edges"])


def test_advisory_reproducible_and_local_audit(fixture_site):
    request = analysis.ScenarioInput(start="2025-10-26T00:30:00+00:00", hours=1)
    first = analysis.evaluate(request)
    second = analysis.evaluate(request)
    assert first["run_hash"] == second["run_hash"]
    assert first["advisory_only"] is True
    assert first["totals"]["baseline_without_dispatch_unserved_ev_kwh"] > 0
    assert (
        first["totals"]["unserved_ev_kwh"]
        < first["totals"]["baseline_without_dispatch_unserved_ev_kwh"]
    )
    assert all(
        row["ending_soc_pct"] >= load_site_config().battery_min_soc_pct for row in first["schedule"]
    )
    operation_database.migrate()
    alarm = events.alarms("2025-10-26T00:31:00+00:00")[0]
    acknowledge(
        AcknowledgementRequest(
            alarm_id=alarm["id"],
            note="Reviewed source event",
            at="2025-10-26T00:31:00+00:00",
        )
    )
    save_scenario(SaveScenarioRequest(scenario=request))
    restored = scenario_runs.saved_scenario(first["run_hash"])
    assert restored is not None
    assert restored["request"] == request.model_dump()
    assert restored["result"]["run_hash"] == first["run_hash"]
    assert scenario_runs.saved_scenario("unknown") is None
    actions = [event["action"] for event in audit()]
    assert "alarm.acknowledge" in actions and "scenario.save" in actions
    assert {event["actor"] for event in audit()} == {"local"}


def test_baseline_uses_recorded_complete_minutes_and_reports_validation(fixture_site):
    available = forecast.baseline("raw:2025-10-26T00:31")
    first = available["rows"][0]
    assert first["solar"]["predicted_kw"] == 5.0
    assert first["observed_ev"]["predicted_kw"] == 18.0
    assert first["solar"]["recorded_kw"] == 5.0
    assert first["observed_ev"]["recorded_kw"] == 18.0
    assert first["solar"]["validation"]["samples"] == 0
    missing = forecast.baseline("raw:2025-10-26T00:30")
    assert missing["rows"][0]["solar"]["predicted_kw"] is None
    later = forecast.baseline("raw:2025-10-26T01:00")
    assert later["rows"][0]["solar"]["validation"]["samples"] == 1
    assert later["rows"][-1]["solar"]["validation"]["samples"] == 0
    end = forecast.baseline("raw:2025-10-26T01:29")
    assert all(row["solar"]["recorded_kw"] is None for row in end["rows"])


def test_rl_report_rejects_stale_source_and_config(fixture_site, tmp_path, monkeypatch):
    report_path = tmp_path / "rl.json"
    monkeypatch.setenv("TWIN_RL_REPORT", str(report_path))
    report = {
        "mode": "simulated_current_replay",
        "advisory_only": True,
        "source": {
            "sha256": repository.metadata()["source_sha256"],
            "coverage_policy": "complete_fleet_paired_minutes_v1",
            "site_config_sha256": hashlib.sha256(
                json.dumps(load_site_config().model_dump(), sort_keys=True).encode()
            ).hexdigest(),
        },
    }
    report_path.write_text(json.dumps(report))
    assert rl_experiment() == report
    report["source"]["sha256"] = "old-source"
    report_path.write_text(json.dumps(report))
    with pytest.raises(Exception, match="different SOFIE source"):
        rl_experiment()
    report["source"]["sha256"] = repository.metadata()["source_sha256"]
    report["source"]["site_config_sha256"] = "old-config"
    report_path.write_text(json.dumps(report))
    with pytest.raises(Exception, match="different site settings"):
        rl_experiment()


def test_publisher_frame_updates_stream_graph(fixture_site):
    observed = replay.snapshot("raw:2025-10-26T00:31")
    frame = make_frame(
        observed,
        datetime(2025, 10, 26, 0, 31),
        "f9fca3b2-680b-4e1b-8833-55b01025e264",
        0,
    )
    stream = TelemetryStream(store=GraphDouble())
    assert stream.ingest(
        json.dumps(frame).encode(),
        {box["id"] for box in observed["wallboxes"]},
        ("2025-10-26 00:30", "2025-10-26 01:29"),
    )
    assert stream.status()["latest"]["solar_kw"] == observed["solar_kw"]
    assert any(node["kind"] == "charger" for node in stream.graph_status()["nodes"])


def test_reject_alternate_source_path(tmp_path, monkeypatch):
    from backend.configuration.dataset import raw_path

    monkeypatch.setenv("TWIN_RAW_JSON", str(tmp_path / "other.json"))
    with pytest.raises(ValueError, match="pinned"):
        raw_path()


def test_reject_changed_source_and_stale_cache(fixture_site):

    from fastapi import HTTPException

    from backend.configuration.dataset import derived_path, raw_path

    source = raw_path()
    source.write_text(source.read_text() + " ")
    with pytest.raises(ValueError, match="SHA-256"):
        build_replay()
    manifest = derived_path() / "manifest.json"
    content = json.loads(manifest.read_text())
    content["metadata"]["source_sha256"] = "another-source"
    manifest.write_text(json.dumps(content))
    with pytest.raises(HTTPException, match="different SOFIE source"):
        repository.metadata()
