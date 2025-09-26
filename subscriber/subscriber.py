import paho.mqtt.client as mqtt
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
MQTT_TOPIC = "ping-pong"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error(f"Failed to connect: {reason_code}")
    else:
        logging.info(f"Connected with result code {reason_code}")
        client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    logging.info(f"Received: {msg.payload.decode()}")

def main():
    """Main function to connect to MQTT and listen for messages."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logging.info("Attempting to connect to MQTT broker")
            break
        except ConnectionRefusedError:
            logging.warning("Connection refused, retrying in 5 seconds...")
            time.sleep(5)

    client.loop_forever()

if __name__ == '__main__':
    main()
