"""Islanded dispatch as a mixed-integer linear program.

Charge and discharge are mutually exclusive. The objective and energy balance
match the configured advisory weights; HiGHS solves the model through Pyomo.
"""

from __future__ import annotations

from fastapi import HTTPException


def optimize(
    slots: list[dict],
    *,
    capacity_kwh: float,
    initial_kwh: float,
    max_power_kw: float,
    reserve_kwh: float,
    one_way_efficiency: float,
    step_hours: float,
    unserved_weight: float,
    curtailment_weight: float,
    throughput_weight: float,
) -> list[dict]:
    pyo, highs = _solver()
    model = pyo.ConcreteModel()
    model.steps = pyo.RangeSet(0, len(slots) - 1)
    model.charge = pyo.Var(model.steps, domain=pyo.NonNegativeReals)
    model.discharge = pyo.Var(model.steps, domain=pyo.NonNegativeReals)
    model.unmet = pyo.Var(model.steps, domain=pyo.NonNegativeReals)
    model.curtail = pyo.Var(model.steps, domain=pyo.NonNegativeReals)
    model.stored = pyo.Var(model.steps, bounds=(reserve_kwh, capacity_kwh))
    model.charging = pyo.Var(model.steps, domain=pyo.Binary)

    def exclusive_charge(model, step):
        return model.charge[step] <= max_power_kw * model.charging[step]

    def exclusive_discharge(model, step):
        return model.discharge[step] <= max_power_kw * (1 - model.charging[step])

    def power_balance(model, step):
        slot = slots[step]
        return (
            model.discharge[step] - model.charge[step] + model.unmet[step] - model.curtail[step]
            == slot["observed_charging_kw"] - slot["solar_kw"]
        )

    def energy_balance(model, step):
        previous = initial_kwh if step == 0 else model.stored[step - 1]
        return model.stored[step] == previous + (
            one_way_efficiency * model.charge[step] - model.discharge[step] / one_way_efficiency
        ) * step_hours

    def unmet_limit(model, step):
        return model.unmet[step] <= slots[step]["observed_charging_kw"]

    def curtail_limit(model, step):
        return model.curtail[step] <= slots[step]["solar_kw"]

    model.exclusive_charge = pyo.Constraint(model.steps, rule=exclusive_charge)
    model.exclusive_discharge = pyo.Constraint(model.steps, rule=exclusive_discharge)
    model.power_balance = pyo.Constraint(model.steps, rule=power_balance)
    model.energy_balance = pyo.Constraint(model.steps, rule=energy_balance)
    model.unmet_limit = pyo.Constraint(model.steps, rule=unmet_limit)
    model.curtail_limit = pyo.Constraint(model.steps, rule=curtail_limit)
    model.objective = pyo.Objective(
        expr=sum(
            throughput_weight * (model.charge[step] + model.discharge[step])
            + unserved_weight * model.unmet[step]
            + curtailment_weight * model.curtail[step]
            for step in model.steps
        )
        * step_hours,
        sense=pyo.minimize,
    )
    result = highs.solve(model)
    if str(result.termination_condition).lower() not in {"optimal", "terminationcondition.optimal"}:
        raise HTTPException(422, f"Advisory MILP could not solve: {result.termination_condition}")
    schedule = []
    for step, slot in enumerate(slots):
        schedule.append(
            {
                **slot,
                "battery_charge_kw": round(float(pyo.value(model.charge[step])), 3),
                "battery_discharge_kw": round(float(pyo.value(model.discharge[step])), 3),
                "unserved_ev_kw": round(float(pyo.value(model.unmet[step])), 3),
                "curtailed_pv_kw": round(float(pyo.value(model.curtail[step])), 3),
                "ending_soc_pct": round(float(pyo.value(model.stored[step]) / capacity_kwh * 100), 2),
                "charging_mode": bool(round(float(pyo.value(model.charging[step])))),
            }
        )
    return schedule


def _solver():
    import pyomo.environ as pyo
    from pyomo.contrib.appsi.solvers.highs import Highs

    solver = Highs()
    solver.config.load_solution = True
    return pyo, solver
