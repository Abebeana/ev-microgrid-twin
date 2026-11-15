"""Application entry point and lifecycle composition."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.metrics import observe
from backend.api.router import router
from backend.operations import database
from backend.streaming import mqtt_subscriber
from backend.telemetry import history
from backend.topology.neo4j_store import graph_store

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        try:
            graph_store.verify()
        except Exception as error:
            raise RuntimeError("Neo4j is required to start the API") from error
        database.migrate()
        source = history.site()
        mqtt_subscriber.start_subscriber(
            {box["id"] for box in source["wallboxes"]},
            (source["metadata"]["first_raw"][:16], source["metadata"]["last_raw"][:16]),
        )
        log.info("Microgrid API started with historical replay and simulated MQTT stream")
        yield
    finally:
        mqtt_subscriber.stop_subscriber()
        graph_store.close()


async def require_neo4j(request: Request, call_next):
    try:
        connected = graph_store.ping()["connected"]
    except Exception:
        connected = False
    if not connected:
        return JSONResponse(status_code=503, content={"detail": "Neo4j is required and unavailable"})
    return await call_next(request)


def create_app() -> FastAPI:
    application = FastAPI(title="EV Microgrid Twin", version="1.0.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.middleware("http")(require_neo4j)
    application.middleware("http")(observe)
    application.include_router(router)
    return application


app = create_app()
