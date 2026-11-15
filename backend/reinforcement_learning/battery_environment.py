"""Battery dispatch simulator for the measured EV/PV subset of an islanded site."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt

from .training_dataset import Episode, Slot

# Positive action is battery discharge to the AC bus; negative is PV charging.
ACTION_FRACTIONS = (-1.0, -0.5, 0.0, 0.5, 1.0)
IDLE_ACTION = 2


@dataclass(frozen=True)
class Outcome:
    source_time: str
    solar_kw: float
    observed_ev_kw: float
    requested_battery_kw: float
    battery_kw: float
    unserved_ev_kwh: float
    curtailed_pv_kwh: float
    battery_throughput_kwh: float
    ending_soc_pct: float
    minimum_reporting_wallboxes: int


class BatteryDispatchEnvironment:
    def __init__(self, episode: Episode, config: dict):
        if not episode.slots:
            raise ValueError("An episode needs at least one interval")
        self.episode = episode
        self.config = config
        self.capacity = float(config["battery_capacity_kwh"])
        self.max_power = float(config["battery_max_power_kw"])
        self.reserve = self.capacity * float(config["battery_min_soc_pct"]) / 100
        self.eta = sqrt(float(config["battery_model_efficiency"]))
        self.dt = float(config["optimizer_step_minutes"]) / 60
        self.index = 0
        self.energy = 0.0
        self.reset()

    def reset(self) -> tuple[int, int, int]:
        self.index = 0
        soc = self.episode.slots[0].measured_soc_pct
        if not self.config["battery_min_soc_pct"] <= soc <= 100:
            raise ValueError("Measured starting SoC is outside the modeled reserve bounds")
        self.energy = self.capacity * soc / 100
        return self.state()

    def state(self) -> tuple[int, int, int]:
        slot = self.episode.slots[self.index]
        reserve_pct = float(self.config["battery_min_soc_pct"])
        soc_bin = min(15, int((self.energy / self.capacity * 100 - reserve_pct) // 5))
        net = slot.observed_ev_kw - slot.solar_kw
        edges = (-15, -8, -4, -1, 1, 4, 8, 15)
        net_bin = sum(net > edge for edge in edges)
        hour = datetime.fromisoformat(slot.source_time).hour
        hour_bin = hour // 4
        return (max(0, soc_bin), net_bin, hour_bin)

    def step(self, action: int) -> tuple[Outcome, float, bool]:
        if not 0 <= action < len(ACTION_FRACTIONS):
            raise ValueError(f"Invalid battery action: {action}")
        return self.apply(ACTION_FRACTIONS[action])

    def apply(self, fraction: float) -> tuple[Outcome, float, bool]:
        fraction = min(1.0, max(-1.0, float(fraction)))
        slot = self.episode.slots[self.index]
        requested = fraction * self.max_power
        surplus = max(slot.solar_kw - slot.observed_ev_kw, 0.0)
        deficit = max(slot.observed_ev_kw - slot.solar_kw, 0.0)
        if requested < 0:
            # Charging uses observed PV surplus only; there is no utility grid.
            charging = min(
                -requested,
                surplus,
                (self.capacity - self.energy) / (self.dt * self.eta),
            )
            battery_kw = -max(charging, 0.0)
            self.energy += -battery_kw * self.dt * self.eta
        else:
            discharging = min(requested, deficit, (self.energy - self.reserve) * self.eta / self.dt)
            battery_kw = max(discharging, 0.0)
            self.energy -= battery_kw * self.dt / self.eta
        self.energy = min(self.capacity, max(self.reserve, self.energy))
        unserved = max(deficit - max(battery_kw, 0.0), 0.0) * self.dt
        curtailed = max(surplus - max(-battery_kw, 0.0), 0.0) * self.dt
        throughput = abs(battery_kw) * self.dt
        outcome = Outcome(
            slot.source_time,
            slot.solar_kw,
            slot.observed_ev_kw,
            requested,
            battery_kw,
            unserved,
            curtailed,
            throughput,
            self.energy / self.capacity * 100,
            slot.minimum_reporting_wallboxes,
        )
        scale = float(self.config["optimizer_unserved_weight"])
        reward = -(
            unserved
            + float(self.config["optimizer_curtailment_weight"]) / scale * curtailed
            + float(self.config["optimizer_throughput_weight"]) / scale * throughput
        )
        self.index += 1
        return outcome, reward, self.index == len(self.episode.slots)


def greedy_action(slot: Slot) -> int:
    if slot.observed_ev_kw > slot.solar_kw:
        return 4
    if slot.solar_kw > slot.observed_ev_kw:
        return 0
    return IDLE_ACTION
