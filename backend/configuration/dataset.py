"""Pinned input identity and local replay CSV locations."""

from __future__ import annotations

import json
import os
from pathlib import Path

from backend.configuration.paths import PROJECT_ROOT

CONTRACT_PATH = Path(
    os.environ.get("TWIN_SOURCE_CONTRACT", PROJECT_ROOT / "config/telemetry-source.json")
)
SOURCE_CONTRACT = json.loads(CONTRACT_PATH.read_text())
_configured_raw = Path(SOURCE_CONTRACT["path"])
DEFAULT_RAW = _configured_raw if _configured_raw.is_absolute() else PROJECT_ROOT / _configured_raw
DEFAULT_DERIVED = PROJECT_ROOT / "data/processed/replay"


def raw_path() -> Path:
    path = Path(os.environ.get("TWIN_RAW_JSON", DEFAULT_RAW))
    if path.resolve() != DEFAULT_RAW.resolve():
        raise ValueError(f"Telemetry source is pinned to {DEFAULT_RAW}")
    return path


def derived_path() -> Path:
    return Path(os.environ.get("TWIN_REPLAY_DIR", DEFAULT_DERIVED))
