"""Perfect-lookahead LP bound, labeled separately from deployable policies."""

from __future__ import annotations

from math import sqrt

import numpy as np
from scipy.optimize import linprog

from .battery_environment import Outcome
from .training_dataset import Episode


def solve(episode: Episode, config: dict) -> list[Outcome]:
    n = len(episode.slots)
    capacity = float(config["battery_capacity_kwh"])
    max_power = float(config["battery_max_power_kw"])
    reserve = capacity * float(config["battery_min_soc_pct"]) / 100
    eta = sqrt(float(config["battery_model_efficiency"]))
    dt = float(config["optimizer_step_minutes"]) / 60
    initial = min(capacity, max(reserve, capacity * episode.slots[0].measured_soc_pct / 100))
    objective = np.zeros(5 * n)
    bounds = []
    equalities = np.zeros((2 * n, 5 * n))
    rhs = np.zeros(2 * n)
    for i, slot in enumerate(episode.slots):
        j = 5 * i
        objective[j : j + 5] = [float(config["optimizer_throughput_weight"]) * dt] * 2 + [
            float(config["optimizer_unserved_weight"]) * dt,
            float(config["optimizer_curtailment_weight"]) * dt,
            0,
        ]
        bounds.extend(
            [
                (0, max_power),
                (0, max_power),
                (0, slot.observed_ev_kw),
                (0, slot.solar_kw),
                (reserve, capacity),
            ]
        )
        equalities[2 * i, j : j + 5] = [-1, 1, 1, -1, 0]
        rhs[2 * i] = slot.observed_ev_kw - slot.solar_kw
        equalities[2 * i + 1, j : j + 5] = [-eta * dt, dt / eta, 0, 0, 1]
        if i:
            equalities[2 * i + 1, j - 1] = -1
        else:
            rhs[2 * i + 1] = initial
    result = linprog(objective, A_eq=equalities, b_eq=rhs, bounds=bounds, method="highs")
    if not result.success:
        raise ValueError(f"Oracle LP failed: {result.message}")
    outcomes = []
    for i, slot in enumerate(episode.slots):
        charge, discharge, unmet, curtailed, ending = result.x[5 * i : 5 * i + 5]
        outcomes.append(
            Outcome(
                slot.source_time,
                slot.solar_kw,
                slot.observed_ev_kw,
                float(discharge - charge),
                float(discharge - charge),
                max(0.0, float(unmet)) * dt,
                max(0.0, float(curtailed)) * dt,
                float(charge + discharge) * dt,
                float(ending / capacity * 100),
                slot.minimum_reporting_wallboxes,
            )
        )
    return outcomes
