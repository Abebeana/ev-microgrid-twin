"""HTTP endpoints for streaming."""

from __future__ import annotations

from fastapi import APIRouter

from backend.streaming import state as stream_state

router = APIRouter(tags=["streaming"])


@router.get("/api/demo-stream")
def demo_stream_status():
    return stream_state.stream.status()


@router.get("/api/demo-stream/graph")
def demo_stream_graph():
    return stream_state.stream.graph_status()
