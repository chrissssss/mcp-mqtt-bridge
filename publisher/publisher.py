import paho.mqtt.client as mqtt
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
MQTT_TOPIC = "ping-pong"

def main():
    """Main function to connect to MQTT, and publish messages periodically."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            logging.info("Successfully connected to MQTT broker")
            break
        except ConnectionRefusedError:
            logging.warning("Connection refused, retrying in 5 seconds...")
            time.sleep(5)

    client.loop_start()

    message_count = 0
    while True:
        message = f"ping {message_count}"
        client.publish(MQTT_TOPIC, message)
        logging.info(f"Sent: {message}")
        message_count += 1
        time.sleep(10)

if __name__ == '__main__':
    main()
