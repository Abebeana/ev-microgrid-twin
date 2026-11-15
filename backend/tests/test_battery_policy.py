import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.reinforcement_learning.battery_environment import (
    BatteryDispatchEnvironment,
)
from backend.reinforcement_learning.evaluation import build_report
from backend.reinforcement_learning.q_learning import QLearningPolicy, train
from backend.reinforcement_learning.training_dataset import Episode, Slot, load_dataset

CONFIG = {
    **json.loads((Path(__file__).resolve().parents[2] / "config/site.json").read_text()),
    "islanded": True,
    "grid_connection": None,
    "optimizer_step_minutes": 15,
    "optimizer_min_coverage_pct": 80,
    "battery_capacity_kwh": 38.4,
    "battery_max_power_kw": 18,
    "battery_min_soc_pct": 20,
    "battery_model_efficiency": 0.9,
    "source_timestamp_timezone": "UTC",
    "optimizer_unserved_weight": 1000,
    "optimizer_curtailment_weight": 1,
    "optimizer_throughput_weight": 0.01,
}


def slot(time, solar, ev, soc=50):
    return Slot(time, solar, ev, soc, 15, 15, 1)


def test_islanded_energy_balance_and_reserve():
    episode = Episode(
        (
            slot("2026-06-01 12:00", 10, 5),
            slot("2026-06-01 12:15", 0, 20),
            slot("2026-06-01 12:30", 0, 20),
        )
    )
    env = BatteryDispatchEnvironment(episode, CONFIG)
    start = env.energy
    charge, _, _ = env.step(0)
    assert charge.battery_kw == -5  # only the available PV surplus
    assert charge.unserved_ev_kwh == 0
    assert env.energy > start
    discharge, _, _ = env.step(4)
    assert 0 < discharge.battery_kw <= 18
    assert discharge.ending_soc_pct < charge.ending_soc_pct
    env.step(4)
    assert env.energy >= env.reserve - 1e-9


def test_no_grid_charging_when_pv_is_missing():
    env = BatteryDispatchEnvironment(Episode((slot("2026-06-01 12:00", 0, 10),)), CONFIG)
    charge, _, done = env.step(0)
    assert done and charge.battery_kw == 0
    assert charge.unserved_ev_kwh == pytest.approx(2.5)


def test_train_test_split_clock_shift_and_policy_roundtrip(tmp_path, monkeypatch):
    from backend.configuration.dataset import SOURCE_CONTRACT

    monkeypatch.setitem(SOURCE_CONTRACT, "sha256", "synthetic-source-hash")
    from backend.configuration.provenance import ingestion_fingerprint
    from backend.configuration.site import SiteConfig
    from backend.ingestion.replay_schema import SCHEMA_VERSION, TABLES
    from backend.storage.replay_writer import ReplayWriter

    replay = tmp_path / "replay"
    writer = ReplayWriter(replay)
    microgrid = []
    charging = []
    for day in (1, 2):
        for offset in range(60):
            minute = datetime(2026, 6, day, 12, 0) + timedelta(minutes=offset)
            raw = minute.strftime("%Y-%m-%d %H:%M")
            microgrid.append((raw, 1, 8, 1, 55, 25, None, 0, 0))
            charging.append((raw, "WB1", 6, 1, raw + ":00"))
    tables = {
        "microgrid_minute": microgrid,
        "charger_minute": charging,
        "wallbox": [("WB1", "Test", "Test", "1")],
    }
    for name in TABLES:
        writer.table(name, tables.get(name, []))
    writer.publish(
        {
            "schema_version": SCHEMA_VERSION,
            "first_raw": "2026-06-01 00:00:00",
            "last_raw": "2026-06-02 23:59:00",
            "source_sha256": "synthetic-source-hash",
            "ingestion_config_sha256": ingestion_fingerprint(SiteConfig.model_validate(CONFIG)),
        }
    )
    config_path = tmp_path / "site.json"
    config_path.write_text(json.dumps(CONFIG))
    dataset = load_dataset(replay, config_path, test_days=1)
    assert len(dataset.train) == len(dataset.test) == 1
    assert dataset.train[0].start == "2026-06-01 12:00"
    assert dataset.test[0].start == "2026-06-02 12:00"
    assert len(dataset.test[0].slots) == 4
    policy = train(dataset.train, CONFIG, iterations=30, seed=7)
    policy_path = tmp_path / "policy.json"
    policy.save(policy_path, {"source_sha256": dataset.source_sha256})
    restored = QLearningPolicy.load(policy_path)
    assert restored.visits == policy.visits
    report = build_report(
        dataset,
        restored,
        "policy-hash",
        datetime(2026, 11, 6, 12, tzinfo=timezone.utc),
        30,
        7,
    )
    assert report["source"]["test_first"] == "2026-06-02 00:00"
    assert report["points"][0]["source_time"] == "2026-06-02 12:00"
    assert report["points"][0]["simulated_at"].startswith("2026-11-06T00:01")
    assert (
        report["totals"]["oracle"]["unserved_ev_kwh"]
        <= report["totals"]["greedy"]["unserved_ev_kwh"]
    )


def test_rejects_replay_from_another_source(tmp_path):
    from backend.ingestion.replay_schema import SCHEMA_VERSION, TABLES
    from backend.storage.replay_writer import ReplayWriter

    replay = tmp_path / "replay"
    writer = ReplayWriter(replay)
    for name in TABLES:
        writer.table(name, [])
    writer.publish({"source_sha256": "other-source", "schema_version": SCHEMA_VERSION})
    config = tmp_path / "site.json"
    config.write_text(json.dumps(CONFIG))
    with pytest.raises(ValueError, match="different SOFIE source"):
        load_dataset(replay, config)


def test_simulator_does_not_invent_energy_below_reserve():
    with pytest.raises(ValueError, match="starting SoC"):
        BatteryDispatchEnvironment(Episode((slot("2026-06-01 12:00", 0, 10, 5),)), CONFIG)


def test_soft_actor_critic_stays_within_the_inverter_fraction():
    from backend.reinforcement_learning.sac_policy import SacPolicy

    episode = Episode(
        tuple(slot(f"2026-06-01 12:{15 * index:02d}", 10, 4, 60) for index in range(4))
    )
    policy = SacPolicy.train((episode,), CONFIG, timesteps=64, seed=3, net_arch=(32, 32))
    env = BatteryDispatchEnvironment(episode, CONFIG)
    env.reset()
    fraction, fallback = policy.fraction(env)
    assert fallback is False
    assert -1 <= fraction <= 1
    report = build_report(
        SimpleNamespace(
            train=(episode,),
            test=(episode,),
            source_sha256="synthetic",
            source_first="2026-06-01 12:00",
            source_last="2026-06-01 12:45",
            test_first="2026-06-01 12:00",
            test_last="2026-06-01 12:45",
            config=CONFIG,
            rejected_slots=0,
        ),
        policy,
        "hash",
        datetime(2026, 11, 8, tzinfo=timezone.utc),
        64,
        3,
    )
    assert report["experiment"]["algorithm"] == "soft_actor_critic"
    assert report["experiment"]["rl_greedy_fallback_steps"] == 0
