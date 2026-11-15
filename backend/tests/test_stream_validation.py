"""The simulated MQTT boundary accepts known, ordered, finite telemetry only."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from backend.streaming.state import TelemetryStream
from backend.tests.graph_double import GraphDouble


def frame(sequence: int = 1) -> dict:
    return {
        "source": "sofie-historical-demo",
        "sequence": sequence,
        "run_id": "4d718cc3-2c10-4d97-ab71-014191344fd9",
        "recorded_at": "2026-06-29T13:45:00",
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "solar_kw": 5.0,
        "battery_soc_pct": 20.0,
        "battery_temp_c": 36.0,
        "wallboxes": [
            {"id": "WB1", "power_kw": 6.0, "status": "Faulted", "status_stale": False},
            {
                "id": "WB2",
                "power_kw": None,
                "status": "Available",
                "status_stale": False,
            },
        ],
    }


def test_stream_validation_and_derived_state(monkeypatch):
    monkeypatch.setenv(
        "TWIN_SITE_CONFIG",
        str(Path(__file__).resolve().parents[2] / "config/site.json"),
    )
    stream = TelemetryStream(store=GraphDouble())
    known = {"WB1", "WB2"}
    assert stream.ingest(json.dumps(frame()).encode(), known)
    result = stream.status()
    assert result["accepted"] == 1
    assert result["latest"]["observed_ev_kw"] == 6.0
    assert result["latest"]["reporting_wallboxes"] == 1
    assert result["latest"]["pv_minus_observed_ev_kw"] == -1.0
    assert len(result["latest"]["alerts"]) == 4
    graph = stream.graph_status()
    assert {node["kind"] for node in graph["nodes"]} >= {
        "site",
        "solar",
        "battery",
        "bus",
        "charger",
        "telemetry_sample",
        "alert",
    }
    assert any(edge["relation"] == "CONNECTED_TO" for edge in graph["edges"])
    assert any(edge["relation"] == "ABOUT" for edge in graph["edges"])
    assert not stream.ingest(json.dumps(frame()).encode(), known)  # duplicate sequence
    bad = frame(2)
    bad["solar_kw"] = float("nan")
    assert not stream.ingest(json.dumps(bad).encode(), known)
    bad = frame(2)
    bad["wallboxes"][1]["id"] = "UNLISTED"
    assert not stream.ingest(json.dumps(bad).encode(), known)
    assert stream.status()["rejected"] == 3
    assert stream.status()["accepted"] == 1
    restarted = frame(0)
    restarted["run_id"] = "740418fa-ed72-4d88-8101-dd847dd86a85"
    assert stream.ingest(json.dumps(restarted).encode(), known)
    assert len(stream.status()["history"]) == 1
    outside = frame(1)
    outside["run_id"] = restarted["run_id"]
    assert not stream.ingest(
        json.dumps(outside).encode(), known, ("2026-06-30 00:00", "2026-07-01 00:00")
    )


def test_site_totals_are_not_copied_to_multiple_assets(monkeypatch, tmp_path):
    config = json.loads((Path(__file__).resolve().parents[2] / "config/site.json").read_text())
    config["assets"].extend(
        [
            {"id": "PV2", "name": "Second PV", "kind": "solar", "connected_to": "BUS"},
            {
                "id": "BESS2",
                "name": "Second battery",
                "kind": "battery",
                "connected_to": "BUS",
            },
        ]
    )
    config_path = tmp_path / "site.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setenv("TWIN_SITE_CONFIG", str(config_path))
    stream = TelemetryStream(store=GraphDouble())
    assert stream.ingest(json.dumps(frame()).encode(), {"WB1", "WB2"})
    nodes = {node["id"]: node for node in stream.graph_status()["nodes"]}
    for asset_id in ("PV", "PV2", "BESS", "BESS2"):
        assert nodes[f"asset:{asset_id}"]["value"] is None
