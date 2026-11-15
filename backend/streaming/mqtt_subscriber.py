"""MQTT subscription lifecycle and frame delivery to the state store."""

from __future__ import annotations

import os

import paho.mqtt.client as mqtt

from backend.streaming.contracts import TOPIC
from backend.streaming.state import stream

client: mqtt.Client | None = None


def start_subscriber(known_wallboxes: set[str], source_window: tuple[str, str]) -> None:
    global client
    host = os.environ.get("TWIN_MQTT_HOST", "127.0.0.1").strip()
    if not host:
        raise ValueError("TWIN_MQTT_HOST must name the MQTT broker")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sofie-twin-api")

    def on_connect(_client, _userdata, _flags, reason_code, _properties):
        with stream.lock:
            stream.broker_connected = not reason_code.is_failure
        if not reason_code.is_failure:
            _client.subscribe(TOPIC, qos=1)

    def on_disconnect(_client, _userdata, _flags, _reason_code, _properties):
        with stream.lock:
            stream.broker_connected = False

    def on_message(_client, _userdata, message):
        stream.ingest(message.payload, known_wallboxes, source_window)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.connect_async(host, int(os.environ.get("TWIN_MQTT_PORT", "1883")), keepalive=30)
    client.loop_start()


def stop_subscriber() -> None:
    global client
    if client is not None:
        client.disconnect()
        client.loop_stop()
        client = None
    with stream.lock:
        stream.broker_connected = False
