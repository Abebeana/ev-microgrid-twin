"""Neo4j traversals for the island, alert exposure, and retained minutes."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from backend.configuration.site import load_site_config
from backend.topology.neo4j_store import Neo4jGraphStore
from backend.topology.projection import project_snapshot


@pytest.fixture
def neo4j_store():
    store = Neo4jGraphStore(prefix=f"test-{uuid4().hex}-")
    try:
        store.verify()
    except Exception:
        store.close()
        raise
    try:
        yield store
    finally:
        try:
            store.clear()
        finally:
            store.close()


def _minute(config, recorded_at: str, *, solar_kw: float, soc: float, temp: float, wallboxes: list[dict]):
    return project_snapshot(
        config,
        recorded_at=recorded_at,
        solar_kw=solar_kw,
        battery_soc_pct=soc,
        battery_temp_c=temp,
        wallboxes=wallboxes,
    )


def test_neo4j_answers_island_paths_and_keeps_both_minutes(neo4j_store, monkeypatch):
    monkeypatch.setenv(
        "TWIN_SITE_CONFIG",
        str(Path(__file__).resolve().parents[2] / "config/site.json"),
    )
    config = load_site_config()
    faulted = [
        {"id": "WB1", "power_kw": 6.0, "status": "Faulted", "status_stale": False},
        {"id": "WB2", "power_kw": None, "status": "Available", "status_stale": False},
    ]
    first = _minute(
        config,
        "2026-06-29 13:45",
        solar_kw=5.0,
        soc=20.0,
        temp=36.0,
        wallboxes=faulted,
    )
    neo4j_store.commit("replay", first["nodes"], first["edges"], record_history=True)
    analytics = neo4j_store.analyze("replay")
    assert analytics["engine"] == "Cypher"
    assert analytics["utility_nodes"] == 0
    assert analytics["islanded"] is True
    downstream = {row["charger_id"]: row for row in analytics["downstream"]}
    assert downstream["wallbox:WB1"]["path"] == ["asset:BUS", "wallbox:WB1"]
    assert downstream["wallbox:WB1"]["power_kw"] == 6.0
    assert downstream["wallbox:WB2"]["path"][-1] == "wallbox:WB2"
    paths = {
        (row["source"], row["target"]): row["hops"] for row in analytics["electrical_paths"]
    }
    assert paths[("asset:PV", "wallbox:WB1")] == ["asset:PV", "asset:BUS", "wallbox:WB1"]
    assert paths[("asset:BESS", "wallbox:WB2")] == ["asset:BESS", "asset:BUS", "wallbox:WB2"]
    by_rule = {row["rule"]: row for row in analytics["alerts"]}
    assert "asset:BESS" in by_rule["low_soc"]["about"]
    assert "asset:BUS" in by_rule["low_soc"]["exposed"]
    assert "wallbox:WB1" in by_rule["low_soc"]["exposed"]
    assert by_rule["charger_fault"]["about"] == ["wallbox:WB1"]
    assert "asset:BESS" in by_rule["charger_fault"]["exposed"]
    attribution = {row["id"]: row for row in analytics["attribution"]}
    assert attribution["asset:PV"]["attributed"] is True
    assert attribution["asset:PV"]["attribution"] == "single_asset"
    labels = {row["label"] for row in analytics["census"]["labels"]}
    assert {"Site", "Solar", "Battery", "Bus", "Charger", "TelemetrySample", "Alert"} <= labels

    second = _minute(
        config,
        "2026-06-29 14:00",
        solar_kw=4.0,
        soc=19.0,
        temp=30.0,
        wallboxes=faulted,
    )
    neo4j_store.commit("stream", second["nodes"], second["edges"], record_history=True)
    neo4j_store.commit("replay", first["nodes"], first["edges"], record_history=True)
    retained = neo4j_store.history_summary()
    assert retained["samples"] == 2
    assert {row["recorded_at"] for row in retained["recent"]} == {
        "2026-06-29 13:45",
        "2026-06-29 14:00",
    }
    exposure = {
        (row["rule"], row["asset_id"]): row["minutes"] for row in retained["repeated_exposure"]
    }
    assert exposure[("charger_fault", "wallbox:WB1")] == 2
    assert exposure[("low_soc", "asset:BESS")] == 2
    trace = {
        (row["charger_id"], row["recorded_at"]): row["power_kw"] for row in retained["charger_trace"]
    }
    assert trace[("wallbox:WB1", "2026-06-29 13:45")] == 6.0
    assert trace[("wallbox:WB2", "2026-06-29 14:00")] is None
    stored = {node["id"]: node for node in neo4j_store.read("replay")["nodes"]}
    assert stored["asset:PV"]["value"] == 5.0
    assert stored["wallbox:WB1"]["wallbox_id"] == "WB1"
