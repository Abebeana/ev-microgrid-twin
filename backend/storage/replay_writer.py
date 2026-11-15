"""Publish complete CSV generations using a single atomic JSON manifest."""

import csv
import json
import os
import shutil
from pathlib import Path
from uuid import uuid4

from backend.ingestion.replay_schema import KEYS, TABLES
from backend.ingestion.value_conversion import sha256
from backend.storage.atomic import sync_directory, write_json


class ReplayWriter:
    def __init__(self, destination: Path):
        self.destination = destination
        self.generation = uuid4().hex
        self.directory = destination / "generations" / self.generation
        self.directory.mkdir(parents=True)
        self.files = {}
        self.published = False

    def table(self, name: str, rows) -> int:
        columns = TABLES[name]
        records = [dict(zip(columns, row, strict=True)) for row in rows]
        records.sort(key=lambda row: tuple(row[key] for key in KEYS[name]))
        previous = None
        path = self.directory / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            for row in records:
                key = tuple(row[column] for column in KEYS[name])
                if key == previous:
                    raise ValueError(f"Duplicate {name} key: {key}")
                previous = key
                writer.writerow(row)
            stream.flush()
            os.fsync(stream.fileno())
        self.files[name] = {"rows": len(records), "sha256": sha256(path)}
        return len(records)

    def publish(self, metadata: dict) -> None:
        if set(self.files) != set(TABLES):
            raise ValueError("Cannot publish an incomplete replay generation")
        sync_directory(self.directory)
        sync_directory(self.directory.parent)
        write_json(
            self.destination / "manifest.json",
            {
                "generation": self.generation,
                "metadata": {key: str(value) for key, value in metadata.items()},
                "tables": self.files,
            },
        )
        self.published = True

    def close(self) -> None:
        if self.published:
            return
        # A directory-sync error can happen after the manifest was replaced.
        # Never delete a generation that readers may already be using.
        try:
            manifest = json.loads((self.destination / "manifest.json").read_text())
        except FileNotFoundError:
            manifest = {}
        except (OSError, ValueError):
            return  # Preserve data when publication status cannot be established.
        if manifest.get("generation") != self.generation:
            shutil.rmtree(self.directory)
