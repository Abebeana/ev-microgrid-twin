"""Validated CSV reads with cached time indexes; no query-language emulation."""

import csv
import json
import math
import re
from bisect import bisect_left, bisect_right
from functools import lru_cache
from pathlib import Path
from threading import RLock

from backend.configuration.dataset import SOURCE_CONTRACT
from backend.ingestion.replay_schema import SCHEMA_VERSION, TABLES
from backend.ingestion.value_conversion import sha256


class ReplayStore:
    def __init__(self, root: Path, manifest: dict):
        generation = manifest["generation"]
        if not re.fullmatch(r"[0-9a-f]{32}", generation):
            raise ValueError("Invalid replay generation")
        self.directory = root / "generations" / generation
        self.metadata = manifest["metadata"]
        self.files = manifest["tables"]
        if self.metadata.get("source_sha256") != SOURCE_CONTRACT["sha256"]:
            raise ValueError("Replay uses a different SOFIE source; rebuild from the pinned JSON")
        if self.metadata.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Replay schema changed; rebuild the CSV files")
        if set(self.files) != set(TABLES):
            raise ValueError("Replay manifest has missing or unknown tables")
        self._tables = {}
        self._signatures = {}
        self._indexes = {}
        self._lock = RLock()

    def table(self, name: str) -> tuple[dict, ...]:
        with self._lock:
            path = self.directory / f"{name}.csv"
            stat = path.stat()
            signature = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size, stat.st_ino)
            if name not in self._tables or self._signatures[name] != signature:
                if sha256(path) != self.files[name]["sha256"]:
                    raise ValueError(f"Replay integrity check failed: {name}")
                schema = TABLES[name]
                with path.open(newline="", encoding="utf-8") as stream:
                    reader = csv.DictReader(stream)
                    if reader.fieldnames != list(schema):
                        raise ValueError(f"Replay columns changed: {name}")
                    rows = tuple(
                        {key: self._convert(value, schema[key]) for key, value in row.items()}
                        for row in reader
                    )
                if len(rows) != self.files[name]["rows"]:
                    raise ValueError(f"Replay row count changed: {name}")
                self._tables[name] = rows
                self._signatures[name] = signature
            return self._tables[name]

    @staticmethod
    def _convert(value, kind):
        if value is None:
            raise ValueError("Malformed CSV row")
        if value == "":
            return None
        result = kind(value)
        if kind is float and not math.isfinite(result):
            raise ValueError("Non-finite replay measurement")
        return result

    def _index(self, name: str, field: str, wallbox_id: str | None):
        key = (name, field, wallbox_id)
        with self._lock:
            self.table(name)  # Detect tampering even after a time index is cached.
            if key not in self._indexes:
                rows = sorted(
                    (
                        row
                        for row in self.table(name)
                        if wallbox_id is None or row["wallbox_id"] == wallbox_id
                    ),
                    key=lambda row: row[field],
                )
                self._indexes[key] = ([row[field] for row in rows], rows)
            return self._indexes[key]

    def between(self, name, start, end, field="raw_minute", wallbox_id=None, end_inclusive=True):
        times, rows = self._index(name, field, wallbox_id)
        stop = bisect_right(times, end) if end_inclusive else bisect_left(times, end)
        return rows[bisect_left(times, start) : stop]

    def latest(self, name, at, field="raw_minute", wallbox_id=None):
        times, rows = self._index(name, field, wallbox_id)
        index = bisect_right(times, at) - 1
        return rows[index] if index >= 0 else None

    def charging_totals(self, start="", end="9999"):
        totals = {}
        for row in self.between("charger_minute", start, end):
            minute = row["raw_minute"]
            group = totals.setdefault(minute, {"raw_minute": minute, "power_kw": 0.0, "boxes": 0})
            group["power_kw"] += row["power_kw"]
            group["boxes"] += 1
        return list(totals.values())


@lru_cache(maxsize=1)
def _load(root: Path, manifest_text: str) -> ReplayStore:
    return ReplayStore(root, json.loads(manifest_text))


def read_replay(root: Path) -> ReplayStore:
    store = _load(root.resolve(), (root / "manifest.json").read_text(encoding="utf-8"))
    if store.metadata["source_sha256"] != SOURCE_CONTRACT["sha256"]:
        raise ValueError("Replay uses a different SOFIE source; rebuild from the pinned JSON")
    return store
