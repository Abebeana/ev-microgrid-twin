"""Publish a time-compressed SOFIE replay through MQTT for classroom demonstration."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import paho.mqtt.client as mqtt

from backend.streaming.contracts import TOPIC
from backend.telemetry import history as replay


def make_frame(snapshot: dict, recorded_at: datetime, run_id: str, sequence: int) -> dict:
    return {
        "source": "sofie-historical-demo",
        "run_id": run_id,
        "sequence": sequence,
        "recorded_at": recorded_at.isoformat(timespec="minutes"),
        "emitted_at": datetime.now(timezone.utc).isoformat(),
        "solar_kw": snapshot["solar_kw"],
        "battery_soc_pct": snapshot["battery_soc_pct"],
        "battery_temp_c": snapshot["battery_temp_c"],
        "wallboxes": [
            {
                "id": box["id"],
                "power_kw": box["power_kw"],
                "status": box["status"],
                "status_stale": box["status_stale"],
            }
            for box in snapshot["wallboxes"]
        ],
    }


def publish_frame(client: mqtt.Client, payload: dict) -> None:
    """Wait for the broker handshake and retry if the connection drops."""
    while True:
        if not client.is_connected():
            time.sleep(0.2)
            continue
        try:
            client.publish(TOPIC, json.dumps(payload, allow_nan=False), qos=1).wait_for_publish()
            return
        except RuntimeError:
            time.sleep(0.2)


def run() -> None:
    site = replay.site()
    first = datetime.fromisoformat(site["default_raw"])
    last = datetime.fromisoformat(site["metadata"]["last_raw"][:16])
    current = first
    interval = max(0.5, float(os.environ.get("TWIN_DEMO_INTERVAL_SECONDS", "3")))
    host = os.environ.get("TWIN_MQTT_HOST", "mqtt")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sofie-demo-publisher")
    while True:
        try:
            client.connect(host, int(os.environ.get("TWIN_MQTT_PORT", "1883")), keepalive=30)
            break
        except OSError:
            time.sleep(2)
    client.loop_start()
    run_id = str(uuid4())
    sequence = 0
    try:
        while True:
            snapshot = replay.snapshot("raw:" + current.isoformat(timespec="minutes"))
            payload = make_frame(snapshot, current, run_id, sequence)
            publish_frame(client, payload)
            sequence += 1
            current += timedelta(minutes=15)
            if current > last:
                current = first
            time.sleep(interval)
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    run()
