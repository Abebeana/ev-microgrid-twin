"""Validate experiment provenance before presenting results."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from fastapi import HTTPException

from backend.configuration.paths import PROJECT_ROOT
from backend.configuration.site import load_site_config
from backend.reinforcement_learning.training_dataset import COVERAGE_POLICY
from backend.telemetry.repository import metadata


def load_report():
    report_path = Path(
        os.environ.get(
            "TWIN_RL_REPORT",
            PROJECT_ROOT / "reports/reinforcement_learning/evaluation.json",
        )
    )
    if not report_path.is_file():
        raise HTTPException(503, "PowerWise RL experiment has not been generated")
    try:
        report = json.loads(report_path.read_text())
        if report["source"]["sha256"] != metadata()["source_sha256"]:
            raise HTTPException(
                409,
                "PowerWise RL report uses a different SOFIE source; rerun the experiment",
            )
        current_config_hash = hashlib.sha256(
            json.dumps(load_site_config().model_dump(), sort_keys=True).encode()
        ).hexdigest()
        if report["source"]["site_config_sha256"] != current_config_hash:
            raise HTTPException(
                409,
                "PowerWise RL report uses different site settings; rerun the experiment",
            )
        if report["source"].get("coverage_policy") != COVERAGE_POLICY:
            raise HTTPException(409, "PowerWise RL coverage rules changed; rerun the experiment")
        if report["mode"] != "simulated_current_replay" or not report["advisory_only"]:
            raise ValueError("Unexpected report mode")
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
        raise HTTPException(503, "PowerWise RL report is invalid; rerun the experiment") from error
    return report
