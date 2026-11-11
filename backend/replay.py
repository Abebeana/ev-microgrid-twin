import json
import time
import pandas as pd
from pathlib import Path
import paho.mqtt.client as mqtt

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "integrated_microgrid_15min.csv"

# MQTT settings
BROKER = "localhost"
PORT = 1883
TOPIC = "microgrid/telemetry"

# Replay settings
REPLAY_INTERVAL = 1
TEST_RECORDS = 5


def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
    df = df.sort_values("timestamp")
    return df


def main():
    df = load_data()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="microgrid_replay"
    )

    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print(f"Connected to MQTT broker at {BROKER}:{PORT}")
    print(f"Starting replay of {len(df)} records...")

    try:
        for _, row in df.head(TEST_RECORDS).iterrows():
            record = row.astype(object).where(pd.notna(row), None).to_dict()
            record["timestamp"] = pd.Timestamp(record["timestamp"]).isoformat()

            payload = json.dumps(record, allow_nan=False)

            result = client.publish(TOPIC, payload, qos=1)
            result.wait_for_publish()

            print(f"Published: {record['timestamp']}")
            time.sleep(REPLAY_INTERVAL)

    except KeyboardInterrupt:
        print("\nReplay stopped.")

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()