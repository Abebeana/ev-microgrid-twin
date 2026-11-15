"""Scale a PyBaMM Thevenin cell to the configured pack and step it forward."""

from __future__ import annotations

NOMINAL_CELL_VOLTAGE = 3.7
PACK_VOLTAGE_TARGET = 400.0


def simulate(
    *,
    pack_kwh: float,
    soc_pct: float,
    power_kw: float,
    ambient_c: float | None,
    minutes: int = 15,
) -> dict:
    pybamm = _pybamm()
    model = pybamm.equivalent_circuit.Thevenin()
    parameters = model.default_parameter_values
    parameters["Initial SoC"] = min(max(soc_pct / 100, 0.02), 0.98)
    if ambient_c is not None and "Ambient temperature [K]" in parameters:
        parameters["Ambient temperature [K]"] = ambient_c + 273.15
        parameters["Initial temperature [K]"] = ambient_c + 273.15
    capacity_ah = float(parameters["Cell capacity [A.h]"])
    cell_kwh = capacity_ah * NOMINAL_CELL_VOLTAGE / 1000
    series = max(1, round(PACK_VOLTAGE_TARGET / NOMINAL_CELL_VOLTAGE))
    parallel = max(1, round(pack_kwh / (series * cell_kwh)))
    cell_current = abs(power_kw) * 1000 / (series * NOMINAL_CELL_VOLTAGE * parallel)
    cell_current = min(cell_current, 2 * capacity_ah)
    if cell_current < 0.05:
        step = f"Rest for {minutes} minutes"
        direction = "idle"
    elif power_kw >= 0:
        step = f"Discharge at {cell_current:.3f} A for {minutes} minutes"
        direction = "discharge"
    else:
        step = f"Charge at {cell_current:.3f} A for {minutes} minutes"
        direction = "charge"
    simulation = pybamm.Simulation(
        model,
        parameter_values=parameters,
        experiment=pybamm.Experiment([step]),
    )
    solution = simulation.solve()
    cell_voltage = float(solution["Voltage [V]"].entries[-1])
    ending_soc = float(solution["SoC"].entries[-1])
    temperature = float(solution["Cell temperature [degC]"].entries[-1])
    return {
        "model": "PyBaMM Thevenin equivalent circuit",
        "direction": direction,
        "minutes": minutes,
        "pack_power_kw": round(power_kw, 3),
        "cell_current_a": round(cell_current, 3),
        "series_cells": series,
        "parallel_cells": parallel,
        "cell_capacity_ah": capacity_ah,
        "modeled_pack_kwh": round(series * parallel * cell_kwh, 2),
        "starting_soc_pct": round(soc_pct, 2),
        "ending_soc_pct": round(ending_soc * 100, 2),
        "cell_voltage_v": round(cell_voltage, 3),
        "pack_voltage_v": round(cell_voltage * series, 1),
        "cell_temperature_c": round(temperature, 2),
        "assumption": (
            f"{series}s{parallel}p of the default {capacity_ah:.0f} Ah Thevenin cell "
            f"is scaled toward {pack_kwh:.1f} kWh and {PACK_VOLTAGE_TARGET:.0f} V. "
            "Positive power discharges the pack."
        ),
    }


def _pybamm():
    import pybamm

    return pybamm
