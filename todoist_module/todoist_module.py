import os
import paho.mqtt.client as mqtt
import json
import logging
import time
from todoist_api_python.api import TodoistAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

# --- Tool Definition ---
TOOL_DEFINITION = {
    "name": "add_task",
    "description": "Adds a new task to Todoist.",
    "parameters": [
        {
            "name": "content",
            "type": "string",
            "description": "The content of the task.",
            "required": True
        }
    ]
}

# --- MQTT Client ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT Broker!")
        client.subscribe("mcp/commands/add_task")
        register_tool(client)
    else:
        logging.error(f"Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    logging.info(f"Received message on topic {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        correlation_id = payload.get("correlation_id")
        params = payload.get("params", {})
        content = params.get("content")

        if not content:
            result = {"error": "Content is required."}
        else:
            try:
                api = TodoistAPI(TODOIST_API_KEY)
                task = api.add_task(content=content)
                result = {"status": "success", "task_id": task.id}
            except Exception as e:
                logging.error(f"Error adding task to Todoist: {e}")
                result = {"error": str(e)}

        response_topic = f"mcp/results/add_task/{correlation_id}"
        client.publish(response_topic, json.dumps(result))
        logging.info(f"Published result to {response_topic}")

    except json.JSONDecodeError:
        logging.error("Failed to decode JSON payload.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


def register_tool(client):
    """Publishes the tool definition to the registration topic."""
    client.publish("mcp/register", json.dumps(TOOL_DEFINITION))
    logging.info("Published tool definition to mcp/register.")

def main():
    if not TODOIST_API_KEY:
        logging.error("TODOIST_API_KEY environment variable not set. Exiting.")
        return

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.loop_forever()
        except ConnectionRefusedError:
            logging.error("Connection to MQTT broker refused. Retrying in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}. Retrying in 5 seconds...")
            time.sleep(5)


if __name__ == "__main__":
    main()
