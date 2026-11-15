"""Validated stream state, alerts, and the current property graph."""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from pydantic import ValidationError

from backend.configuration.site import load_site_config
from backend.streaming.contracts import TOPIC, TelemetryFrame
from backend.topology.neo4j_store import graph_store
from backend.topology.projection import project_snapshot


class TelemetryStream:
    def __init__(self, store=None):
        self.lock = Lock()
        self.broker_connected = False
        self.accepted = 0
        self.rejected = 0
        self.last_error: str | None = None
        self.latest: dict | None = None
        self.history: deque[dict] = deque(maxlen=60)
        self.store = store or graph_store
        self.storage_error: str | None = None

    def ingest(
        self,
        payload: bytes,
        known_wallboxes: set[str],
        source_window: tuple[str, str] | None = None,
    ) -> bool:
        try:
            frame = TelemetryFrame.model_validate_json(payload)
            if {box.id for box in frame.wallboxes} != known_wallboxes:
                raise ValueError("wallbox inventory differs from SOFIE source")
            recorded = frame.recorded_at.strftime("%Y-%m-%d %H:%M")
            if source_window and not source_window[0] <= recorded <= source_window[1]:
                raise ValueError("recorded timestamp is outside the SOFIE source window")
            with self.lock:
                if (
                    self.latest
                    and str(frame.run_id) == self.latest["run_id"]
                    and frame.sequence <= self.latest["sequence"]
                ):
                    raise ValueError("sequence is not newer than the last accepted frame")
                if self.latest and str(frame.run_id) != self.latest["run_id"]:
                    self.history.clear()
                observed = [box.power_kw for box in frame.wallboxes if box.power_kw is not None]
                ev_kw = sum(observed) if observed else None
                config = load_site_config()
                received_at = datetime.now(timezone.utc).isoformat()
                projected = project_snapshot(
                    config,
                    recorded_at=frame.recorded_at.strftime("%Y-%m-%d %H:%M"),
                    received_at=received_at,
                    solar_kw=frame.solar_kw,
                    battery_soc_pct=frame.battery_soc_pct,
                    battery_temp_c=frame.battery_temp_c,
                    wallboxes=[box.model_dump() for box in frame.wallboxes],
                )
                record = frame.model_dump(mode="json")
                record.update(
                    {
                        "observed_ev_kw": ev_kw,
                        "reporting_wallboxes": len(observed),
                        "pv_minus_observed_ev_kw": frame.solar_kw - ev_kw
                        if frame.solar_kw is not None and ev_kw is not None
                        else None,
                        "alerts": [alert["name"] for alert in projected["alerts"]],
                        "received_at": received_at,
                    }
                )
                try:
                    self.store.commit(
                        "stream", projected["nodes"], projected["edges"], record_history=True
                    )
                except Exception as error:
                    self.storage_error = str(error).splitlines()[0]
                    return False
                self.storage_error = None
                self.latest = record
                self.accepted += 1
                self.last_error = None
                self.history.append(
                    {
                        "recorded_at": record["recorded_at"],
                        "solar_kw": frame.solar_kw,
                        "observed_ev_kw": ev_kw,
                        "battery_soc_pct": frame.battery_soc_pct,
                    }
                )
            return True
        except (ValidationError, ValueError, json.JSONDecodeError) as error:
            with self.lock:
                self.rejected += 1
                self.last_error = str(error).splitlines()[0]
            return False

    def graph_status(self) -> dict:
        payload = {"mode": "simulated_historical_stream", "store": self.store.name}
        try:
            payload.update(self.store.read("stream"))
            payload["analytics"] = self.store.analyze("stream")
            payload["history"] = self.store.history_summary()
        except Exception as error:
            payload.update(
                {
                    "nodes": [],
                    "edges": [],
                    "error": str(error).splitlines()[0][:240],
                }
            )
        return payload

    def status(self) -> dict:
        with self.lock:
            latest = self.latest.copy() if self.latest else None
            age = (
                max(
                    0,
                    (
                        datetime.now(timezone.utc) - datetime.fromisoformat(latest["received_at"])
                    ).total_seconds(),
                )
                if latest
                else None
            )
            return {
                "mode": "simulated_historical_stream",
                "topic": TOPIC,
                "broker_connected": self.broker_connected,
                "fresh": bool(self.broker_connected and age is not None and age < 10),
                "age_seconds": round(age, 1) if age is not None else None,
                "accepted": self.accepted,
                "rejected": self.rejected,
                "last_error": self.last_error,
                "storage_error": self.storage_error,
                "latest": latest,
                "history": list(self.history),
            }


stream = TelemetryStream()
