"""HTTP endpoint for the validated battery policy evaluation."""

from __future__ import annotations

from fastapi import APIRouter

from backend.reinforcement_learning.report import load_report

router = APIRouter(tags=["reinforcement learning"])


@router.get("/api/rl/experiment")
def rl_experiment():
    return load_report()
