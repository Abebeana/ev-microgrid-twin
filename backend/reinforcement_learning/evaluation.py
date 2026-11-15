"""Compare trained policies with baseline and perfect-lookahead dispatch."""

import hashlib
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .battery_environment import (
    ACTION_FRACTIONS,
    BatteryDispatchEnvironment,
    Outcome,
    greedy_action,
)
from .perfect_foresight import solve
from .training_dataset import COVERAGE_POLICY, Dataset, Episode


def _run(
    episode: Episode, config: dict, kind: str, policy=None
) -> tuple[list[Outcome], int]:
    if kind == "oracle":
        return solve(episode, config), 0
    env = BatteryDispatchEnvironment(episode, config)
    env.reset()
    outcomes = []
    fallbacks = 0
    for slot in episode.slots:
        if kind == "rl":
            fraction, fallback = policy.fraction(env)
            fallbacks += int(fallback)
        elif kind == "greedy":
            fraction, fallback = ACTION_FRACTIONS[greedy_action(slot)], False
        else:
            fraction = 0.0
        outcome, _, _done = env.apply(fraction)
        outcomes.append(outcome)
    return outcomes, fallbacks


def _totals(outcomes: list[Outcome]) -> dict[str, float]:
    return {
        "unserved_ev_kwh": round(sum(row.unserved_ev_kwh for row in outcomes), 3),
        "curtailed_pv_kwh": round(sum(row.curtailed_pv_kwh for row in outcomes), 3),
        "battery_throughput_kwh": round(sum(row.battery_throughput_kwh for row in outcomes), 3),
    }


def _shifted_time(raw: str, shift: timedelta, zone: str) -> str:
    source = datetime.fromisoformat(raw).replace(tzinfo=ZoneInfo(zone)).astimezone(timezone.utc)
    return (source + shift).isoformat()


def build_report(
    dataset: Dataset,
    policy,
    policy_hash: str,
    anchor: datetime,
    iterations: int,
    seed: int,
) -> dict:
    zone = dataset.config["source_timestamp_timezone"]
    source_end = (
        datetime.fromisoformat(dataset.source_last)
        .replace(tzinfo=ZoneInfo(zone))
        .astimezone(timezone.utc)
    )
    shift = anchor - source_end
    methods = ("idle", "greedy", "rl", "oracle")
    all_outcomes: dict[str, list[Outcome]] = {name: [] for name in methods}
    daily: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    points = []
    fallbacks = 0
    for episode in dataset.test:
        result = {name: _run(episode, dataset.config, name, policy) for name in methods}
        for name in methods:
            all_outcomes[name].extend(result[name][0])
        fallbacks += result["rl"][1]
        for index, slot in enumerate(episode.slots):
            row = {
                "source_time": slot.source_time,
                "simulated_at": _shifted_time(slot.source_time, shift, zone),
                "solar_kw": round(slot.solar_kw, 3),
                "observed_ev_kw": round(slot.observed_ev_kw, 3),
                "pv_minutes": slot.pv_minutes,
                "ev_minutes": slot.ev_minutes,
                "minimum_reporting_wallboxes": slot.minimum_reporting_wallboxes,
                "measured_start_soc_pct": round(episode.slots[0].measured_soc_pct, 2)
                if index == 0
                else None,
                "outcomes": {
                    name: {
                        "battery_kw": round(result[name][0][index].battery_kw, 3),
                        "unserved_ev_kwh": round(result[name][0][index].unserved_ev_kwh, 4),
                        "curtailed_pv_kwh": round(result[name][0][index].curtailed_pv_kwh, 4),
                        "ending_soc_pct": round(result[name][0][index].ending_soc_pct, 2),
                    }
                    for name in methods
                },
            }
            points.append(row)
    for name in methods:
        by_day: dict[str, list[Outcome]] = defaultdict(list)
        for outcome in all_outcomes[name]:
            by_day[outcome.source_time[:10]].append(outcome)
        for day, rows in by_day.items():
            daily[day][name] = _totals(rows)
    test_steps = sum(len(episode.slots) for episode in dataset.test)
    report = {
        "mode": "simulated_current_replay",
        "advisory_only": True,
        "scope": "Measured PV and observed EV charging subset; other site loads are unavailable",
        "clock_note": "simulated_at is a display-time shift of recorded history, not a live measurement or future forecast",
        "source": {
            "sha256": dataset.source_sha256,
            "coverage_policy": COVERAGE_POLICY,
            "site_config_sha256": hashlib.sha256(
                json.dumps(dataset.config, sort_keys=True).encode()
            ).hexdigest(),
            "first": dataset.source_first,
            "last": dataset.source_last,
            "timezone_interpretation": zone,
            "test_first": dataset.test_first,
            "test_last": dataset.test_last,
            "test_days": (
                datetime.fromisoformat(dataset.test_last).date()
                - datetime.fromisoformat(dataset.test_first).date()
            ).days
            + 1,
            "simulated_current_at": anchor.isoformat(),
            "simulated_shift_seconds": int(shift.total_seconds()),
        },
        "experiment": {
            "algorithm": getattr(policy, "algorithm", "tabular_q_learning"),
            "policy_sha256": policy_hash,
            "seed": seed,
            "training_iterations": iterations,
            "training_episodes": len(dataset.train),
            "training_steps": sum(len(episode.slots) for episode in dataset.train),
            "test_episodes": len(dataset.test),
            "test_steps": test_steps,
            "excluded_low_coverage_slots": dataset.rejected_slots,
            "rl_greedy_fallback_steps": fallbacks,
            "minimum_coverage_pct": dataset.config["optimizer_min_coverage_pct"],
            "minimum_episode_steps": 4,
            "battery_capacity_kwh": dataset.config["battery_capacity_kwh"],
            "battery_max_power_kw": dataset.config["battery_max_power_kw"],
            "battery_min_soc_pct": dataset.config["battery_min_soc_pct"],
            "assumed_round_trip_efficiency": dataset.config["battery_model_efficiency"],
            "comparison_note": "Oracle sees each full test episode in advance. Soft Actor-Critic and the simple rule see only the current measured PV, EV load, and battery state.",
        },
        "totals": {name: _totals(all_outcomes[name]) for name in methods},
        "daily": [{"source_day": day, "methods": daily[day]} for day in sorted(daily)],
        "points": points,
    }
    report["run_hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    return report
