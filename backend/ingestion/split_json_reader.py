"""Bounded-memory reader for SOFIE's indented pandas split-format JSON export."""

from __future__ import annotations

import json
import mmap
from pathlib import Path
from typing import Iterator


class SplitJsonReader:
    """Decode one row at a time from the multi-gigabyte read-only source."""

    def __init__(self, path: Path):
        self.path = path
        self.stream = None
        self.data = None
        self.tables: dict[str, tuple[list[str], int, int]] = {}

    def __enter__(self) -> "SplitJsonReader":
        self.stream = self.path.open("rb")
        self.data = mmap.mmap(self.stream.fileno(), 0, access=mmap.ACCESS_READ)
        return self

    def __exit__(self, *_: object) -> None:
        if self.data is not None:
            self.data.close()
        if self.stream is not None:
            self.stream.close()

    def _table(self, name: str) -> tuple[list[str], int, int]:
        if name in self.tables:
            return self.tables[name]
        data = self.data
        assert data is not None
        start = data.find(f'\n  "{name}": {{'.encode())
        if start < 0:
            raise ValueError(f"Missing SOFIE JSON table: {name}")
        next_table = data.find(b'\n  "', start + 1)
        end = next_table if next_table >= 0 else len(data)
        columns_at = data.find(b'"columns": [', start, end)
        rows_at = data.find(b'"data": [', start, end)
        if columns_at < 0 or rows_at < columns_at:
            raise ValueError(f"Invalid SOFIE JSON table layout: {name}")
        columns_start = data.find(b"[", columns_at, rows_at)
        columns_end = data.find(b"\n    ]", columns_start, rows_at)
        if columns_start < 0 or columns_end < 0:
            raise ValueError(f"Invalid SOFIE JSON columns: {name}")
        columns = json.loads(data[columns_start : columns_end + len(b"\n    ]")])
        if not isinstance(columns, list) or len(columns) != len(set(columns)):
            raise ValueError(f"Invalid SOFIE JSON column names: {name}")
        rows_start = data.find(b"[", rows_at, end) + 1
        self.tables[name] = (columns, rows_start, end)
        return self.tables[name]

    def indices(self, name: str, required: tuple[str, ...]) -> dict[str, int]:
        columns = self._table(name)[0]
        missing = set(required) - set(columns)
        if missing:
            raise ValueError(f"Missing {name} columns: {', '.join(sorted(missing))}")
        return {column: columns.index(column) for column in required}

    def rows(self, name: str) -> Iterator[list]:
        columns, position, section_end = self._table(name)
        data = self.data
        assert data is not None
        while position < section_end:
            while data[position] in b" \t\r\n,":
                position += 1
            if data[position] == ord("]"):
                return
            if data[position] != ord("["):
                raise ValueError(f"Invalid {name} row at byte {position}")
            # The export places each closing row bracket on its own line.
            close = data.find(b"\n      ]", position, section_end)
            if close < 0:
                raise ValueError(f"Unterminated {name} row at byte {position}")
            position_after = close + len(b"\n      ]")
            row = json.loads(data[position:position_after])
            if not isinstance(row, list) or len(row) != len(columns):
                raise ValueError(f"Wrong number of values in {name} row at byte {position}")
            yield row
            position = position_after
        raise ValueError(f"Unterminated SOFIE JSON data array: {name}")
