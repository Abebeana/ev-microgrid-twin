"""Deterministic battery dispatch optimization over observed EV and PV load."""

from __future__ import annotations

import hashlib
import json
from math import sqrt

from fastapi import HTTPException

from backend.configuration.site import load_site_config
from backend.optimization.contracts import ScenarioInput
from backend.optimization.inputs import scenario_inputs
from backend.optimization.milp import optimize
from backend.telemetry.repository import metadata


def evaluate(request: ScenarioInput) -> dict:
    config = load_site_config()
    slots, initial_soc_pct = scenario_inputs(request)
    capacity = request.battery_capacity_kwh or config.battery_capacity_kwh
    reserve = capacity * config.battery_min_soc_pct / 100
    initial_kwh = capacity * initial_soc_pct / 100
    if initial_kwh < reserve:
        raise HTTPException(422, "Measured starting SoC is below the configured advisory reserve")
    eta = sqrt(config.battery_model_efficiency)
    dt = config.optimizer_step_minutes / 60
    schedule = optimize(
        slots,
        capacity_kwh=capacity,
        initial_kwh=initial_kwh,
        max_power_kw=config.battery_max_power_kw,
        reserve_kwh=reserve,
        one_way_efficiency=eta,
        step_hours=dt,
        unserved_weight=config.optimizer_unserved_weight,
        curtailment_weight=config.optimizer_curtailment_weight,
        throughput_weight=config.optimizer_throughput_weight,
    )
    meta = metadata()
    provenance = {
        "source_sha256": meta["source_sha256"],
        "coverage_policy": "complete_fleet_paired_minutes_v1",
        "source_timezone": config.source_timestamp_timezone,
        "scenario": request.model_dump(),
        "capacity_kwh": capacity,
        "max_battery_power_kw": config.battery_max_power_kw,
        "min_soc_pct": config.battery_min_soc_pct,
        "assumed_round_trip_efficiency": config.battery_model_efficiency,
        "step_minutes": config.optimizer_step_minutes,
        "coverage_required_pct": config.optimizer_min_coverage_pct,
        "objective_weights": {
            "unserved_ev_kwh": config.optimizer_unserved_weight,
            "curtailed_pv_kwh": config.optimizer_curtailment_weight,
            "battery_throughput_kwh": config.optimizer_throughput_weight,
        },
        "formulation": "Pyomo MILP solved by HiGHS. Charge and discharge cannot occur together.",
        "objective": "Weighted sum of unserved observed EV energy, PV curtailment, and battery throughput",
    }
    fingerprint = hashlib.sha256(
        json.dumps({"provenance": provenance, "slots": slots}, sort_keys=True).encode()
    ).hexdigest()
    return {
        "mode": "historical_what_if",
        "advisory_only": True,
        "scope": "Observed EV charging and PV subset; other site loads and battery inverter readings are excluded",
        "initial_soc_pct": initial_soc_pct,
        "schedule": schedule,
        "totals": {
            "unserved_ev_kwh": round(sum(s["unserved_ev_kw"] * dt for s in schedule), 3),
            "curtailed_pv_kwh": round(sum(s["curtailed_pv_kw"] * dt for s in schedule), 3),
            "battery_discharge_kwh": round(
                sum(s["battery_discharge_kw"] * dt for s in schedule), 3
            ),
            "baseline_without_dispatch_unserved_ev_kwh": round(
                sum(max(s["observed_charging_kw"] - s["solar_kw"], 0) * dt for s in slots),
                3,
            ),
        },
        "provenance": provenance,
        "run_hash": fingerprint,
    }
