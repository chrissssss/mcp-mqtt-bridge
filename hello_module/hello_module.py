import logging
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MQTT Configuration ---
MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
COMMAND_TOPIC = "mcp/commands/hello"
REGISTRATION_TOPIC = "mcp/register"
RESULT_TOPIC = "mcp/results/hello"

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback for when the client connects to the broker."""
    if reason_code == 0:
        logging.info("MQTT client connected successfully.")
        
        logging.info(f"Subscribing to command topic: {COMMAND_TOPIC}")
        client.subscribe(COMMAND_TOPIC)

        tool_def = {
            "name": "hello",
            "description": "Responds with a 'Hello World' message and the current time.",
            "parameters": [
                {"name": "name", "type": "str", "default": "World"}
            ]
        }
        payload = json.dumps(tool_def)
        logging.info(f"Publishing tool definition to '{REGISTRATION_TOPIC}': {payload}")
        client.publish(REGISTRATION_TOPIC, payload, retain=True)
        logging.info("Tool definition published.")

def on_message(client, userdata, msg):
    """Callback for when a command message is received from the broker."""
    try:
        logging.info(f"Received command on topic '{msg.topic}'")
        command_data = json.loads(msg.payload)
        correlation_id = command_data.get("correlation_id")
        
        if not correlation_id:
            logging.warning("Received command without a correlation_id. Ignoring.")
            return

        # --- Create and publish the response ---
        current_time = datetime.now().strftime('%H:%M:%S')
        response_text = f"Hello World at {current_time}"
        
        response_payload = {
            "correlation_id": correlation_id,
            "result": response_text
        }
        
        payload_json = json.dumps(response_payload)
        logging.info(f"Publishing response to '{RESULT_TOPIC}': {payload_json}")
        client.publish(RESULT_TOPIC, payload_json)
        logging.info("Response published.")

    except json.JSONDecodeError:
        logging.error(f"Failed to decode command JSON: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"An error occurred in on_message: {e}")

def main():
    """Main function to connect to MQTT and listen for commands."""
    logging.info("Static module starting up.")
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    except Exception as e:
        logging.error(f"Failed to connect to MQTT broker: {e}")
        return

    logging.info("Starting MQTT client loop (blocking).")
    mqtt_client.loop_forever()

if __name__ == "__main__":
    main()
