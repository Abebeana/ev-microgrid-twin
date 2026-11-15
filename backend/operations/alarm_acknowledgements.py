"""Persist alarm review notes and their audit events."""

from __future__ import annotations

from fastapi import HTTPException

from backend.operations.audit_log import _audit, _now
from backend.operations.database import database


def acknowledge(alarm_id: str, note: str, user: dict) -> dict:
    if not note.strip():
        raise HTTPException(422, "A note is required to acknowledge an alarm")
    with database() as db:
        db.execute(
            "INSERT OR REPLACE INTO alarm_acknowledgement VALUES (?,?,?,?)",
            (alarm_id, user["username"], _now(), note.strip()),
        )
        _audit(db, user, "alarm.acknowledge", alarm_id, {"note": note.strip()})
    return {"alarm_id": alarm_id, "acknowledged_by": user["username"]}


def acknowledgements(ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    with database() as db:
        rows = db.execute(
            f"SELECT * FROM alarm_acknowledgement WHERE alarm_id IN ({','.join('?' for _ in ids)})",
            ids,
        ).fetchall()
    return {r["alarm_id"]: dict(r) for r in rows}
