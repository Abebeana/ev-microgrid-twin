"""Persist and restore reproducible dispatch scenarios."""

from __future__ import annotations

import json

from backend.operations.audit_log import _audit, _now
from backend.operations.database import database


def save_scenario(request: dict, result: dict, user: dict) -> dict:
    run_hash = result["run_hash"]
    with database() as db:
        db.execute(
            "INSERT OR REPLACE INTO scenario_run VALUES (?,?,?,?,?)",
            (
                run_hash,
                user["username"],
                _now(),
                json.dumps(request, sort_keys=True),
                json.dumps(result, sort_keys=True),
            ),
        )
        _audit(
            db,
            user,
            "scenario.save",
            run_hash,
            {"request": request, "totals": result["totals"]},
        )
    return {"run_hash": run_hash, "saved_by": user["username"]}


def saved_scenarios() -> list[dict]:
    with database() as db:
        rows = db.execute(
            "SELECT run_hash,actor,created_at,request_json,result_json FROM scenario_run ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return [
        {
            "run_hash": r["run_hash"],
            "actor": r["actor"],
            "created_at": r["created_at"],
            "request": json.loads(r["request_json"]),
            "totals": json.loads(r["result_json"])["totals"],
        }
        for r in rows
    ]


def saved_scenario(run_hash: str) -> dict | None:
    with database() as db:
        row = db.execute(
            "SELECT run_hash,actor,created_at,request_json,result_json FROM scenario_run WHERE run_hash=?",
            (run_hash,),
        ).fetchone()
    if row is None:
        return None
    return {
        "run_hash": row["run_hash"],
        "actor": row["actor"],
        "created_at": row["created_at"],
        "request": json.loads(row["request_json"]),
        "result": json.loads(row["result_json"]),
    }
