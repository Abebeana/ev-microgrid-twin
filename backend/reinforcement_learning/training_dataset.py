"""Read quality-checked SOFIE intervals without modifying the source store."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from backend.configuration.dataset import derived_path
from backend.configuration.provenance import ingestion_fingerprint
from backend.configuration.site import DEFAULT_CONFIG, SiteConfig
from backend.storage.replay_reader import read_replay

DEFAULT_REPLAY = derived_path()
COVERAGE_POLICY = "complete_fleet_paired_minutes_v1"


@dataclass(frozen=True)
class Slot:
    source_time: str
    solar_kw: float
    observed_ev_kw: float
    measured_soc_pct: float
    pv_minutes: int
    ev_minutes: int
    minimum_reporting_wallboxes: int


@dataclass(frozen=True)
class Episode:
    slots: tuple[Slot, ...]

    @property
    def start(self) -> str:
        return self.slots[0].source_time


@dataclass(frozen=True)
class Dataset:
    train: tuple[Episode, ...]
    test: tuple[Episode, ...]
    source_sha256: str
    source_first: str
    source_last: str
    test_first: str
    test_last: str
    config: dict
    rejected_slots: int


def _episodes(slots: list[Slot], minimum_steps: int = 4) -> tuple[Episode, ...]:
    groups: list[list[Slot]] = []
    previous: datetime | None = None
    for slot in slots:
        current = datetime.fromisoformat(slot.source_time)
        if previous is None or current - previous != timedelta(minutes=15):
            groups.append([])
        groups[-1].append(slot)
        previous = current
    return tuple(Episode(tuple(group)) for group in groups if len(group) >= minimum_steps)


def load_dataset(
    replay_path: Path = DEFAULT_REPLAY, config_path: Path = DEFAULT_CONFIG, test_days: int = 30
) -> Dataset:
    if not replay_path.is_dir():
        raise FileNotFoundError(f"SOFIE derived store is missing: {replay_path}")
    if test_days < 1:
        raise ValueError("test_days must be positive")
    settings = SiteConfig.model_validate(json.loads(config_path.read_text()))
    config = settings.model_dump()
    if config["optimizer_step_minutes"] != 15:
        raise ValueError("This experiment expects 15-minute SOFIE intervals")
    if not config["islanded"] or config["grid_connection"] is not None:
        raise ValueError("This experiment requires the configured islanded site")
    store = read_replay(replay_path)
    metadata = store.metadata
    if metadata.get("ingestion_config_sha256") != ingestion_fingerprint(settings):
        raise ValueError("Ingestion settings changed; rebuild the replay CSV files")
    source_last = metadata["last_raw"][:16]
    source_first = metadata["first_raw"][:16]
    test_last_dt = datetime.fromisoformat(source_last)
    test_first_dt = test_last_dt.replace(hour=0, minute=0) - timedelta(days=test_days - 1)
    test_first = test_first_dt.strftime("%Y-%m-%d %H:%M")
    charging = {row["raw_minute"]: row for row in store.charging_totals()}
    required_boxes = len(store.table("wallbox"))
    rows = (
        {
            **row,
            "ev_kw": charging.get(row["raw_minute"], {}).get("power_kw"),
            "reporting_wallboxes": charging.get(row["raw_minute"], {}).get("boxes", 0),
        }
        for row in store.table("microgrid_minute")
    )
    buckets: dict[str, dict] = {}
    for row in rows:
        minute = row["raw_minute"]
        key = minute[:14] + f"{(int(minute[14:16]) // 15) * 15:02d}"
        bucket = buckets.setdefault(key, {"solar": [], "ev": [], "soc": None, "boxes": []})
        if (
            row["solar_kw"] is not None
            and row["ev_kw"] is not None
            and row["reporting_wallboxes"] == required_boxes
        ):
            bucket["solar"].append(float(row["solar_kw"]))
            bucket["ev"].append(float(row["ev_kw"]))
            bucket["boxes"].append(int(row["reporting_wallboxes"]))
        if minute == key and row["battery_soc_pct"] is not None:
            bucket["soc"] = float(row["battery_soc_pct"])
    threshold = config["optimizer_min_coverage_pct"] / 100 * 15
    accepted: list[Slot] = []
    rejected = 0
    for key, bucket in sorted(buckets.items()):
        if (
            len(bucket["solar"]) < threshold
            or len(bucket["ev"]) < threshold
            or bucket["soc"] is None
            or not config["battery_min_soc_pct"] <= bucket["soc"] <= 100
        ):
            rejected += 1
            continue
        accepted.append(
            Slot(
                source_time=key,
                solar_kw=sum(bucket["solar"]) / len(bucket["solar"]),
                observed_ev_kw=sum(bucket["ev"]) / len(bucket["ev"]),
                measured_soc_pct=bucket["soc"],
                pv_minutes=len(bucket["solar"]),
                ev_minutes=len(bucket["ev"]),
                minimum_reporting_wallboxes=min(bucket["boxes"]),
            )
        )
    train = _episodes([slot for slot in accepted if slot.source_time < test_first])
    test = _episodes([slot for slot in accepted if slot.source_time >= test_first])
    if not train or not test:
        raise ValueError("No sufficiently covered train or test episodes")
    return Dataset(
        train,
        test,
        metadata["source_sha256"],
        source_first,
        source_last,
        test_first,
        source_last,
        config,
        rejected,
    )
