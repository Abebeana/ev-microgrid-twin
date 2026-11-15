"""Physical PV, power flow, MILP dispatch, cell model, and OCPP central system."""

from __future__ import annotations

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.battery.pack import simulate
from backend.charging.ocpp_central import CentralChargePoint
from backend.charging.ocpp_registry import registry
from backend.configuration.site import load_site_config
from backend.electrical.network import solve
from backend.forecasting.clearsky import pvwatts_kw
from backend.forecasting.conformal import intervals
from backend.optimization.milp import optimize


class _Socket:
    async def recv(self) -> str:
        return ""

    async def send(self, message: str) -> None:
        return None


def test_clearsky_peaks_at_midday_in_berlin():
    config = load_site_config()
    zone = ZoneInfo("Europe/Berlin")
    noon, night = pvwatts_kw(
        [
            datetime(2026, 6, 21, 12, tzinfo=zone),
            datetime(2026, 6, 21, 0, tzinfo=zone),
        ],
        config,
        nameplate_kw=10,
    )
    assert noon > 5
    assert night == 0


def test_conformal_interval_covers_a_scaled_clearsky_shape():
    features = [[index / 40, 0.0, 1.0] for index in range(40)]
    measured = [20 * row[0] for row in features]
    result = intervals(features, measured, [[0.5, 0.0, 1.0]])
    assert result["calibrated"] is True
    assert result["lower_kw"][0] <= result["point_kw"][0] <= result["upper_kw"][0]
    assert result["point_kw"][0] == pytest.approx(10, abs=0.5)


def test_power_flow_inverter_balances_the_feeders():
    result = solve(5.0, [("A", 4.0), ("B", 3.0)])
    assert result["converged"] is True
    assert result["inverter_kw"] == pytest.approx(2.0, abs=0.2)
    assert result["minimum_voltage_pu"] < 1
    assert {bus["name"] for bus in result["buses"]} >= {"BESS inverter", "AC bus", "A", "B"}


def test_milp_refuses_simultaneous_charge_and_discharge():
    slots = [
        {"solar_kw": 10.0, "observed_charging_kw": 0.0},
        {"solar_kw": 0.0, "observed_charging_kw": 12.0},
    ]
    schedule = optimize(
        slots,
        capacity_kwh=38.4,
        initial_kwh=20,
        max_power_kw=18,
        reserve_kwh=7.68,
        one_way_efficiency=0.9**0.5,
        step_hours=0.25,
        unserved_weight=1000,
        curtailment_weight=1,
        throughput_weight=0.01,
    )
    assert schedule[0]["battery_charge_kw"] > 0
    assert schedule[0]["battery_discharge_kw"] == 0
    assert schedule[1]["battery_discharge_kw"] > 0
    assert schedule[1]["battery_charge_kw"] == 0
    assert schedule[1]["unserved_ev_kw"] < 12


def test_thevenin_pack_discharges_when_the_island_is_short():
    result = simulate(pack_kwh=38.4, soc_pct=80, power_kw=10, ambient_c=25, minutes=5)
    assert result["direction"] == "discharge"
    assert result["ending_soc_pct"] < result["starting_soc_pct"]
    assert 300 < result["pack_voltage_v"] < 500


def test_ocpp_boot_transaction_and_meter_values():
    registry.points.clear()
    registry._next_transaction = 1
    point = CentralChargePoint("CP-1", _Socket())
    asyncio.run(point.on_boot_notification("ABB", "Terra"))
    asyncio.run(point.on_start_transaction(1, "TAG", 1000, "2026-06-01T12:00:00Z"))
    asyncio.run(
        point.on_meter_values(
            1,
            [
                {
                    "sampled_value": [
                        {"value": "7000", "measurand": "Power.Active.Import", "unit": "W"}
                    ]
                }
            ],
        )
    )
    record = registry.snapshot()["charge_points"][0]
    assert record["vendor"] == "ABB"
    assert record["status"] == "Charging"
    assert record["transaction_id"] == 1
    assert record["power_kw"] == 7
