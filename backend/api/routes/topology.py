"""HTTP endpoint for the recorded microgrid graph."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.topology.neo4j_store import graph_store
from backend.topology.site_graph import build_site_graph

router = APIRouter(tags=["topology"])


@router.get("/api/graph")
def get_graph(at: str | None = None):
    projection = build_site_graph(at)
    try:
        graph_store.commit("replay", projection["nodes"], projection["edges"], record_history=True)
        stored = graph_store.read("replay")
        analytics = graph_store.analyze("replay")
        retained = graph_store.history_summary()
    except Exception as error:
        raise HTTPException(
            503, f"Neo4j graph store is unavailable: {str(error).splitlines()[0][:240]}"
        ) from error
    return {
        "nodes": stored["nodes"],
        "edges": stored["edges"],
        "note": projection["note"],
        "store": graph_store.name,
        "analytics": analytics,
        "history": retained,
    }
