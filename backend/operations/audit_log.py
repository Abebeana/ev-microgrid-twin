"""Actor identity and append-only review audit events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from backend.operations.database import database

LOCAL_ACTOR = {"username": "local", "role": "operator"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(db: sqlite3.Connection, user: dict, action: str, target: str, details: dict) -> None:
    db.execute(
        "INSERT INTO audit_event (occurred_at,actor,action,target,details_json) VALUES (?,?,?,?,?)",
        (_now(), user["username"], action, target, json.dumps(details, sort_keys=True)),
    )


def audit_events(user: dict) -> list[dict]:
    with database() as db:
        return [dict(r) for r in db.execute("SELECT * FROM audit_event ORDER BY id DESC LIMIT 100")]
