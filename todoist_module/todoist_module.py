import os
import paho.mqtt.client as mqtt
import json
import logging
from todoist_api_python.api import TodoistAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TODOIST_API_KEY = os.getenv("TODOIST_API_KEY")

REGISTRATION_TOPIC = "mcp/register"
ADD_TASK_COMMAND_TOPIC = "mcp/commands/add_task"
ADD_TASK_RESULT_TOPIC = "mcp/results/add_task"
LIST_TASKS_COMMAND_TOPIC = "mcp/commands/list_tasks"
LIST_TASKS_RESULT_TOPIC = "mcp/results/list_tasks"

# --- Tool Definitions ---
ADD_TASK_TOOL = {
    "name": "add_task",
    "description": "Adds a new task to Todoist.",
    "parameters": [
        {
            "name": "content",
            "type": "str",
            "description": "The content of the task.",
            "required": True
        }
    ]
}

LIST_TASKS_TOOL = {
    "name": "list_tasks",
    "description": "Lists all active tasks from Todoist.",
    "parameters": []
}

def on_connect(client, userdata, flags, reason_code, properties):
    """Callback for when the client connects to the broker."""
    if reason_code.is_failure:
        logging.error(f"MQTT failed to connect: {reason_code}")
        return
    
    logging.info("MQTT client connected successfully.")
    
    # Subscribe to command topics
    client.subscribe(ADD_TASK_COMMAND_TOPIC)
    logging.info(f"Subscribed to command topic: {ADD_TASK_COMMAND_TOPIC}")
    client.subscribe(LIST_TASKS_COMMAND_TOPIC)
    logging.info(f"Subscribed to command topic: {LIST_TASKS_COMMAND_TOPIC}")

    # Register tools
    client.publish(REGISTRATION_TOPIC, json.dumps(ADD_TASK_TOOL), retain=True)
    logging.info(f"Published tool definition for 'add_task' to '{REGISTRATION_TOPIC}'")
    client.publish(REGISTRATION_TOPIC, json.dumps(LIST_TASKS_TOOL), retain=True)
    logging.info(f"Published tool definition for 'list_tasks' to '{REGISTRATION_TOPIC}'")

def on_message(client, userdata, msg):
    """Callback for when a command message is received."""
    try:
        logging.info(f"Received command on topic '{msg.topic}'")
        command_data = json.loads(msg.payload)
        correlation_id = command_data.get("correlation_id")
        params = command_data.get("params", {})

        if not correlation_id:
            logging.warning("Received command without a correlation_id. Ignoring.")
            return

        api = TodoistAPI(TODOIST_API_KEY)
        result = {}
        result_topic = ""

        if msg.topic == ADD_TASK_COMMAND_TOPIC:
            result_topic = ADD_TASK_RESULT_TOPIC
            content = params.get("content")
            if not content:
                result = {"error": "Content parameter is required."}
            else:
                task = api.add_task(content=content)
                result = {"status": "success", "task_id": task.id, "content": task.content}
        
        elif msg.topic == LIST_TASKS_COMMAND_TOPIC:
            result_topic = LIST_TASKS_RESULT_TOPIC
            tasks = api.get_tasks()
            tasks_list = [{
                "id": task.id, 
                "content": task.content, 
                "due": task.due.string if task.due else None
            } for page_of_tasks in tasks for task in page_of_tasks]
            result = json.dumps(tasks_list, indent=2)

        response_payload = {
            "correlation_id": correlation_id,
            "result": result
        }
        
        client.publish(result_topic, json.dumps(response_payload))
        logging.info(f"Published response to '{result_topic}'")

    except json.JSONDecodeError:
        logging.error(f"Failed to decode command JSON: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"An error occurred in on_message: {e}")
        # Optionally, publish an error response
        if correlation_id and result_topic:
            error_message = f"Error: {str(e)}"
            error_response = {
                "correlation_id": correlation_id,
                "result": error_message
            }
            client.publish(result_topic, json.dumps(error_response))


def main():
    """Main function to connect to MQTT and listen for commands."""
    if not TODOIST_API_KEY:
        logging.error("TODOIST_API_KEY environment variable not set. Exiting.")
        return

    logging.info("Todoist module starting up.")
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