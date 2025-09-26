import paho.mqtt.client as mqtt
import time

MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
MQTT_TOPIC = "ping-pong"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

while True:
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        break
    except ConnectionRefusedError:
        print("Connection refused, retrying in 5 seconds...")
        time.sleep(5)

client.loop_start()

message_count = 0
while True:
    message = f"ping {message_count}"
    client.publish(MQTT_TOPIC, message)
    print(f"Sent: {message}")
    message_count += 1
    time.sleep(10)
