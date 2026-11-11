import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "microgrid/telemetry"

client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="python_test"
)

client.connect(BROKER, PORT, 60)

client.publish(
    TOPIC,
    "Hello from Python!",
    qos=1
)

print("Message published successfully!")

client.disconnect()