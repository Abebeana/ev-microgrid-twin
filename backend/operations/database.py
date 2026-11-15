"""SQLite operation storage and versioned schema migrations."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.configuration.paths import BACKEND_ROOT, PROJECT_ROOT

MIGRATION = Path(
    os.environ.get("TWIN_MIGRATION_SQL", BACKEND_ROOT / "operations/migrations/001_operations.sql")
)


def path() -> Path:
    return Path(
        os.environ.get("TWIN_OPERATIONS_DB", PROJECT_ROOT / "data/runtime/operations.sqlite3")
    )


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    destination = path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(destination, timeout=30)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def migrate() -> None:
    with database() as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            db.executescript(MIGRATION.read_text())
            db.execute("PRAGMA user_version=1")
            db.commit()
