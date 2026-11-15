"""Source null handling, numeric validation, and file fingerprints."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _missing(value: object) -> bool:
    return value is None or value == "None"


def _nullable(value: object) -> object | None:
    return None if _missing(value) else value


def _number(value: object) -> float | None:
    if _missing(value):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None
