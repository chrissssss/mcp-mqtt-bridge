import logging
import paho.mqtt.client as mqtt
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP, Context
import json
from typing import Callable, Coroutine
import queue
import asyncio
import uuid

# Configure logging to a file to bypass library logging conflicts
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Prevent passing messages to the root logger
logger.propagate = False
# Clear existing handlers
if logger.hasHandlers():
    logger.handlers.clear()
# Add a file handler
handler = logging.FileHandler('/app/mcp_server.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# --- MQTT Configuration ---
MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
REGISTRATION_TOPIC = "mcp/register"
RESULT_TOPIC_WILDCARD = "mcp/results/+"

# --- Global state for pending requests ---
pending_futures = {}

def on_result_message(client, userdata, msg):
    """Handles incoming result messages by resolving futures."""
    try:
        logger.info(f"Received result message on topic '{msg.topic}'")
        data = json.loads(msg.payload)
        correlation_id = data.get("correlation_id")
        
        if correlation_id in pending_futures:
            future = pending_futures.pop(correlation_id)
            future.set_result(data.get("result"))
            logger.info(f"Resolved future for correlation_id: {correlation_id}")
        else:
            logger.warning(f"Received result for unknown correlation_id: {correlation_id}")
            
    except json.JSONDecodeError:
        logger.error(f"Failed to decode result JSON: {msg.payload.decode()}")
    except Exception as e:
        logger.error(f"Error processing result message: {e}")


# --- Lifespan Management for MQTT Connection ---
@asynccontextmanager
async def mqtt_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manages the MQTT client's connection and the registration queue."""
    logger.info("MCP server lifespan starting.")
    registration_queue = queue.Queue()

    def on_registration_message(client, userdata, msg):
        """Handles incoming tool registration messages by putting them on a queue."""
        logger.info(f"Received registration message on topic '{msg.topic}'. Adding to queue.")
        registration_queue.put(msg.payload)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error(f"MQTT failed to connect: {reason_code}")
        else:
            logger.info("MQTT client connected successfully.")
            logger.info(f"Subscribing to registration topic: {REGISTRATION_TOPIC}")
            client.subscribe(REGISTRATION_TOPIC)
            logger.info(f"Subscribing to result topic: {RESULT_TOPIC_WILDCARD}")
            client.subscribe(RESULT_TOPIC_WILDCARD)

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add(REGISTRATION_TOPIC, on_registration_message)
    mqtt_client.message_callback_add(RESULT_TOPIC_WILDCARD, on_result_message)

    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    logger.info("MQTT client loop started.")

    queue_processor_task = asyncio.create_task(process_registration_queue(registration_queue))
    logger.info("Tool registration queue processor task created.")

    try:
        yield {"mqtt_client": mqtt_client}
    finally:
        logger.info("MCP server lifespan shutting down.")
        queue_processor_task.cancel()
        try:
            await queue_processor_task
        except asyncio.CancelledError:
            logger.info("Tool registration queue processor task cancelled.")
        
        logger.info("Stopping MQTT client loop.")
        mqtt_client.loop_stop()
        logger.info("Disconnecting MQTT client.")
        mqtt_client.disconnect()

# 1. Create an MCP server instance
mcp = FastMCP(
    "MQTT-MCP Bridge",
    instructions="This server acts as a bridge between the Model Context Protocol and an MQTT network.",
    host="0.0.0.0",
    port=8000,
    lifespan=mqtt_lifespan,
)

# 2. Add a diagnostic tool to check the server's state
@mcp.tool()
def server_status() -> str:
    """Returns the list of currently registered tools on the server."""
    try:
        tool_names = list(mcp._tool_manager._tools.keys())
        logger.info(f"server_status called. Tools: {tool_names}")
        return f"Registered tools: {tool_names}"
    except Exception as e:
        logger.error(f"Error inspecting tools: {e}")
        return f"Error inspecting tools: {e}"

def create_tool_function(tool_name: str, command_topic: str) -> Coroutine:
    """
    Factory to create an async function for a dynamically registered tool.
    
    NOTE: This is a temporary, non-generic implementation to fix a parameter mismatch issue.
    It is hardcoded to the signature of the 'hello' tool.
    """
    logger.info(f"Creating async tool function for '{tool_name}' on topic '{command_topic}'")
    
    async def dynamic_tool(name: str = "World", ctx: Context | None = None) -> str:
        logger.info(f"Async dynamic tool '{tool_name}' called with name: '{name}'")

        if not ctx or not ctx.request_context.lifespan_context:
            msg = f"Tool '{tool_name}': Could not access lifespan context."
            logger.error(msg)
            return f"Error: {msg}"

        mqtt_client = ctx.request_context.lifespan_context.get("mqtt_client")
        if not mqtt_client:
            msg = f"Tool '{tool_name}': Could not access MQTT client from context."
            logger.error(msg)
            return f"Error: {msg}"

        correlation_id = str(uuid.uuid4())
        future = asyncio.get_running_loop().create_future()
        pending_futures[correlation_id] = future

        command_payload = {
            "correlation_id": correlation_id,
            "params": {"name": name} # Package the specific parameter
        }
        
        payload = json.dumps(command_payload)
        mqtt_client.publish(command_topic, payload)
        logger.info(f"Tool '{tool_name}': Published command to {command_topic} with correlation_id: {correlation_id}")

        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            logger.info(f"Tool '{tool_name}': Received result for {correlation_id}: {result}")
            return result
        except asyncio.TimeoutError:
            logger.error(f"Tool '{tool_name}': Timed out waiting for result for correlation_id: {correlation_id}")
            pending_futures.pop(correlation_id, None) # Clean up
            return f"Error: Tool '{tool_name}' timed out."
        except Exception as e:
            logger.error(f"Tool '{tool_name}': An error occurred while waiting for future: {e}")
            return f"Error: An unexpected error occurred in tool '{tool_name}'."

    dynamic_tool.__name__ = tool_name
    return dynamic_tool

def register_tool_from_definition(tool_def_payload: bytes):
    """Parses a tool definition and registers it with the MCP server."""
    logger.info(f"Attempting to register tool from payload: {tool_def_payload}")
    try:
        tool_def = json.loads(tool_def_payload)
        tool_name = tool_def.get("name")
        description = tool_def.get("description", "")
        
        if not tool_name:
            logger.error(f"Registration failed: Tool definition missing 'name'. Payload: {tool_def_payload}")
            return

        command_topic = f"mcp/commands/{tool_name}"
        tool_func = create_tool_function(tool_name, command_topic)
        
        mcp.tool(name=tool_name, description=description)(tool_func)
        logger.info(f"Successfully registered tool: '{tool_name}'")

    except json.JSONDecodeError:
        logger.error(f"Registration failed: Failed to decode JSON from registration message: {tool_def_payload}")
    except Exception as e:
        logger.error(f"Registration failed: An unexpected error occurred: {e}")

async def process_registration_queue(registration_queue: queue.Queue):
    """Continuously checks a queue for new tool registrations and processes them."""
    logger.info("Starting tool registration queue processor.")
    while True:
        try:
            tool_def_payload = registration_queue.get_nowait()
            logger.info(f"Got tool definition from queue. Processing...")
            register_tool_from_definition(tool_def_payload)
        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error in registration queue processor: {e}")

def main():
    """Entry point for the MCP server."""
    logger.info("Starting MCP server with SSE transport on port 8000...")
    mcp.settings.sse_path = "/mcp"
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
