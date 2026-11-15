"""HTTP endpoints for alarms."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.alarms import events as alarm_events
from backend.operations import alarm_acknowledgements
from backend.operations.audit_log import LOCAL_ACTOR

router = APIRouter(tags=["alarms"])


@router.get("/api/alarms")
def get_alarms(at: str | None = None):
    alarms = alarm_events.alarms(at)
    acknowledgements = alarm_acknowledgements.acknowledgements([alarm["id"] for alarm in alarms])
    return [{**alarm, "acknowledgement": acknowledgements.get(alarm["id"])} for alarm in alarms]


class AcknowledgementRequest(BaseModel):
    alarm_id: str
    note: str = Field(min_length=1, max_length=500)
    at: str


@router.post("/api/alarms/acknowledge")
def acknowledge(request: AcknowledgementRequest):
    if request.alarm_id not in {alarm["id"] for alarm in alarm_events.alarms(request.at)}:
        raise HTTPException(404, "Alarm is not present at the selected replay time")
    return alarm_acknowledgements.acknowledge(request.alarm_id, request.note, LOCAL_ACTOR)
