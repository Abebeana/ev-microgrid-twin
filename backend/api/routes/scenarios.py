"""HTTP endpoints for scenarios."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.operations import scenario_runs
from backend.operations.audit_log import LOCAL_ACTOR
from backend.optimization import dispatch

router = APIRouter(tags=["scenarios"])


@router.post("/api/scenarios/evaluate")
def evaluate_scenario(request: dispatch.ScenarioInput):
    return dispatch.evaluate(request)


class SaveScenarioRequest(BaseModel):
    scenario: dispatch.ScenarioInput


@router.post("/api/scenarios/save")
def save_scenario(request: SaveScenarioRequest):
    result = dispatch.evaluate(request.scenario)
    return scenario_runs.save_scenario(request.scenario.model_dump(), result, LOCAL_ACTOR)


@router.get("/api/scenarios/saved")
def saved_scenarios():
    return scenario_runs.saved_scenarios()


@router.get("/api/scenarios/saved/{run_hash}")
def saved_scenario(run_hash: str):
    result = scenario_runs.saved_scenario(run_hash)
    if result is None:
        raise HTTPException(404, "Saved scenario not found")
    return result
