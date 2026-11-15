"""In-test stand-in for the Neo4j store. It does not answer traversals."""

from __future__ import annotations


class GraphDouble:
    name = "test-double"

    def __init__(self):
        self.views: dict[str, dict] = {}
        self.samples = 0

    def commit(self, view: str, nodes: list[dict], edges: list[dict], *, record_history: bool = True) -> None:
        self.views[view] = {
            "nodes": [dict(node) for node in nodes],
            "edges": [dict(edge) for edge in edges],
        }
        if record_history:
            self.samples += 1

    def read(self, view: str) -> dict:
        stored = self.views.get(view, {"nodes": [], "edges": []})
        return {
            "nodes": [dict(node) for node in stored["nodes"]],
            "edges": [dict(edge) for edge in stored["edges"]],
        }

    def analyze(self, view: str) -> dict:
        return {
            "engine": "test-double",
            "utility_nodes": 0,
            "islanded": True,
            "census": {"labels": [], "relations": []},
            "downstream": [],
            "electrical_paths": [],
            "alerts": [],
            "attribution": [],
            "queries": [],
        }

    def history_summary(self) -> dict:
        return {
            "samples": self.samples,
            "alerts": 0,
            "recent": [],
            "charger_trace": [],
            "repeated_exposure": [],
        }
