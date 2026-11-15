"""Migration guards for module ownership, portable defaults, and HTTP compatibility."""

import ast
import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.configuration.dataset import DEFAULT_DERIVED, DEFAULT_RAW
from backend.configuration.paths import PROJECT_ROOT
from backend.main import create_app


def test_application_imports_stay_inside_this_checkout():
    root = PROJECT_ROOT / "backend"
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            imports = []
            if isinstance(node, ast.Import):
                imports = [name.name for name in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            assert not any(
                name.startswith(("ev_microgrid_backend", "powerwise_rl")) for name in imports
            ), path
            if "api" not in path.relative_to(root).parts and path.name != "main.py":
                assert not any(name.startswith("backend.api") for name in imports), path
        module_name = ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)
        module = importlib.import_module(module_name)
        assert Path(module.__file__).resolve().is_relative_to(PROJECT_ROOT)
    assert DEFAULT_RAW.is_relative_to(PROJECT_ROOT / "data/raw")
    assert DEFAULT_DERIVED.is_relative_to(PROJECT_ROOT / "data/processed")


def test_http_routes_preserve_the_workbench_contract():
    paths = create_app().openapi()["paths"]
    expected = {
        "/api/health",
        "/api/site",
        "/api/replay",
        "/api/trend",
        "/api/sessions",
        "/api/chargers/{wallbox_id}/trend",
        "/api/alarms",
        "/api/quality",
        "/api/graph",
        "/api/availability",
        "/api/forecasts/baseline",
        "/api/forecasts/physical",
        "/api/electrical/power-flow",
        "/api/battery/model",
        "/api/chargers/ocpp",
        "/api/rl/experiment",
        "/api/demo-stream",
        "/api/demo-stream/graph",
        "/api/scenarios/evaluate",
        "/api/alarms/acknowledge",
        "/api/scenarios/save",
        "/api/scenarios/saved",
        "/api/scenarios/saved/{run_hash}",
        "/api/audit",
        "/metrics",
    }
    assert set(paths) == expected
    for path in ("/api/scenarios/evaluate", "/api/scenarios/save", "/api/alarms/acknowledge"):
        assert "post" in paths[path]


def test_api_refuses_to_start_without_neo4j(monkeypatch):
    def unavailable():
        raise ConnectionError("Neo4j is down")

    monkeypatch.setattr("backend.main.graph_store.verify", unavailable)
    monkeypatch.setattr("backend.main.graph_store.close", lambda: None)
    monkeypatch.setattr("backend.main.mqtt_subscriber.stop_subscriber", lambda: None)
    with pytest.raises(RuntimeError, match="Neo4j is required to start the API"):
        with TestClient(create_app()):
            pass


def test_api_rejects_requests_after_neo4j_disconnects(monkeypatch):
    connected = {"value": True}
    monkeypatch.setattr("backend.main.graph_store.verify", lambda: None)
    monkeypatch.setattr(
        "backend.main.graph_store.ping", lambda: {"connected": connected["value"]}
    )
    monkeypatch.setattr("backend.main.graph_store.close", lambda: None)
    monkeypatch.setattr("backend.main.database.migrate", lambda: None)
    monkeypatch.setattr(
        "backend.main.history.site",
        lambda: {
            "wallboxes": [],
            "metadata": {"first_raw": "2026-01-01 00:00", "last_raw": "2026-01-01 00:01"},
        },
    )
    monkeypatch.setattr("backend.main.mqtt_subscriber.start_subscriber", lambda *_: None)
    monkeypatch.setattr("backend.main.mqtt_subscriber.stop_subscriber", lambda: None)

    with TestClient(create_app()) as client:
        assert client.get("/api/availability").status_code == 200
        connected["value"] = False
        for path in ("/api/availability", "/api/health", "/metrics"):
            response = client.get(path)
            assert response.status_code == 503
            assert response.json()["detail"] == "Neo4j is required and unavailable"
