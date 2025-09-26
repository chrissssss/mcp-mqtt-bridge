import logging
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MQTT Configuration ---
MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
COMMAND_TOPIC = "mcp/commands/hello"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        logging.error(f"MQTT failed to connect: {reason_code}")
    else:
        logging.info("MQTT client connected successfully.")
        logging.info(f"Subscribing to topic: {COMMAND_TOPIC}")
        client.subscribe(COMMAND_TOPIC)

def on_message(client, userdata, msg):
    logging.info(f"Received message on topic {msg.topic}: {msg.payload.decode()}")

def main():
    """Main function to connect to MQTT and listen for commands."""
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    # connect() is blocking, so we don't need a retry loop here like in the other services
    # as loop_forever() will handle reconnects.
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # loop_forever() is a blocking call that handles reconnects automatically.
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
