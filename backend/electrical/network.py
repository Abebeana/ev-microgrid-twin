"""Low-voltage feeder power flow.

The battery inverter is the grid-forming slack. Each reporting wallbox is a
load at the end of a short feeder. Missing PV or charger power is left out of
the injection and reported as unmeasured.
"""

from __future__ import annotations

FEEDER_LENGTH_KM = 0.03
FEEDER_R_OHM_PER_KM = 0.25
FEEDER_X_OHM_PER_KM = 0.08
FEEDER_MAX_I_KA = 0.4
LV_KV = 0.4


def solve(solar_kw: float | None, chargers: list[tuple[str, float | None]]) -> dict:
    pandapower = _pandapower()
    network = pandapower.create_empty_network(name="SOFIE island", sn_mva=0.25, f_hz=50)
    inverter = pandapower.create_bus(network, vn_kv=LV_KV, name="BESS inverter")
    main = pandapower.create_bus(network, vn_kv=LV_KV, name="AC bus")
    pandapower.create_ext_grid(network, inverter, vm_pu=1.0, name="Grid-forming inverter")
    pandapower.create_line_from_parameters(
        network,
        inverter,
        main,
        FEEDER_LENGTH_KM,
        FEEDER_R_OHM_PER_KM,
        FEEDER_X_OHM_PER_KM,
        0,
        FEEDER_MAX_I_KA,
        name="Inverter feeder",
    )
    measured_solar = solar_kw is not None
    if measured_solar and solar_kw > 0:
        pandapower.create_sgen(network, main, p_mw=solar_kw / 1000, q_mvar=0, name="PV")
    loads = []
    unmeasured = []
    for charger_id, power_kw in chargers:
        if power_kw is None:
            unmeasured.append(charger_id)
            continue
        bus = pandapower.create_bus(network, vn_kv=LV_KV, name=charger_id)
        pandapower.create_line_from_parameters(
            network,
            main,
            bus,
            FEEDER_LENGTH_KM,
            FEEDER_R_OHM_PER_KM,
            FEEDER_X_OHM_PER_KM,
            0,
            FEEDER_MAX_I_KA,
            name=f"{charger_id} feeder",
        )
        pandapower.create_load(network, bus, p_mw=max(power_kw, 0) / 1000, q_mvar=0, name=charger_id)
        loads.append(charger_id)
    try:
        pandapower.runpp(network, algorithm="nr", numba=False, init="flat")
    except TypeError:
        pandapower.runpp(network, algorithm="nr", init="flat")
    if not bool(network.converged):
        return {"converged": False, "reason": "Newton-Raphson power flow did not converge"}
    return _result(network, measured_solar, solar_kw, loads, unmeasured)


def _result(network, measured_solar: bool, solar_kw: float | None, loads, unmeasured) -> dict:
    slack_mw = float(network.res_ext_grid.p_mw.iloc[0])
    buses = [
        {
            "name": str(row["name"]),
            "voltage_pu": round(float(network.res_bus.vm_pu.loc[index]), 4),
            "angle_deg": round(float(network.res_bus.va_degree.loc[index]), 3),
        }
        for index, row in network.bus.iterrows()
    ]
    lines = []
    for index, row in network.line.iterrows():
        i_ka = float(network.res_line.i_ka.loc[index])
        loading = i_ka / float(row.max_i_ka) * 100
        lines.append(
            {
                "name": str(row["name"]),
                "loading_pct": round(loading, 2),
                "current_a": round(i_ka * 1000, 2),
                "power_kw": round(float(network.res_line.p_from_mw.loc[index]) * 1000, 3),
            }
        )
    charging_kw = round(float(network.res_load.p_mw.sum()) * 1000, 3) if len(network.load) else 0.0
    return {
        "converged": True,
        "model": "pandapower Newton-Raphson",
        "islanded": True,
        "forming_source": "Battery inverter modeled as the voltage source",
        "solar_measured": measured_solar,
        "solar_kw": None if solar_kw is None else round(solar_kw, 3),
        "charging_kw": charging_kw,
        "unmeasured_chargers": unmeasured,
        "inverter_kw": round(slack_mw * 1000, 3),
        "inverter_kvar": round(float(network.res_ext_grid.q_mvar.iloc[0]) * 1000, 3),
        "minimum_voltage_pu": round(min(bus["voltage_pu"] for bus in buses), 4),
        "maximum_feeder_loading_pct": round(max(line["loading_pct"] for line in lines), 2),
        "losses_kw": round(
            (slack_mw + (0 if solar_kw is None else solar_kw / 1000) - charging_kw / 1000) * 1000,
            3,
        ),
        "buses": buses,
        "feeders": lines,
        "reporting_chargers": loads,
        "assumptions": {
            "voltage_kv": LV_KV,
            "feeder_length_m": FEEDER_LENGTH_KM * 1000,
            "feeder_rating_a": FEEDER_MAX_I_KA * 1000,
            "power_factor": 1,
            "note": (
                "Feeder impedance and the 400 A rating are study assumptions, "
                "not measured cable data."
            ),
        },
    }


def _pandapower():
    import pandapower

    return pandapower
