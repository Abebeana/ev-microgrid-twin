"""HTTP endpoints for audit."""

from __future__ import annotations

from fastapi import APIRouter

from backend.operations import audit_log

router = APIRouter(tags=["audit"])


@router.get("/api/audit")
def audit():
    return audit_log.audit_events(audit_log.LOCAL_ACTOR)
