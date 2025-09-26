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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        logging.info(f"Received result message on topic '{msg.topic}'")
        data = json.loads(msg.payload)
        correlation_id = data.get("correlation_id")
        
        if correlation_id in pending_futures:
            future = pending_futures.pop(correlation_id)
            future.set_result(data.get("result"))
            logging.info(f"Resolved future for correlation_id: {correlation_id}")
        else:
            logging.warning(f"Received result for unknown correlation_id: {correlation_id}")
            
    except json.JSONDecodeError:
        logging.error(f"Failed to decode result JSON: {msg.payload.decode()}")
    except Exception as e:
        logging.error(f"Error processing result message: {e}")


# --- Lifespan Management for MQTT Connection ---
@asynccontextmanager
async def mqtt_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manages the MQTT client's connection and the registration queue."""
    logging.info("MCP server lifespan starting.")
    registration_queue = queue.Queue()

    def on_registration_message(client, userdata, msg):
        """Handles incoming tool registration messages by putting them on a queue."""
        logging.info(f"Received registration message on topic '{msg.topic}'. Adding to queue.")
        registration_queue.put(msg.payload)

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logging.error(f"MQTT failed to connect: {reason_code}")
        else:
            logging.info("MQTT client connected successfully.")
            logging.info(f"Subscribing to registration topic: {REGISTRATION_TOPIC}")
            client.subscribe(REGISTRATION_TOPIC)
            logging.info(f"Subscribing to result topic: {RESULT_TOPIC_WILDCARD}")
            client.subscribe(RESULT_TOPIC_WILDCARD)

    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add(REGISTRATION_TOPIC, on_registration_message)
    mqtt_client.message_callback_add(RESULT_TOPIC_WILDCARD, on_result_message)

    logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
    logging.info("MQTT client loop started.")

    queue_processor_task = asyncio.create_task(process_registration_queue(registration_queue))
    logging.info("Tool registration queue processor task created.")

    try:
        yield {"mqtt_client": mqtt_client}
    finally:
        logging.info("MCP server lifespan shutting down.")
        queue_processor_task.cancel()
        try:
            await queue_processor_task
        except asyncio.CancelledError:
            logging.info("Tool registration queue processor task cancelled.")
        
        logging.info("Stopping MQTT client loop.")
        mqtt_client.loop_stop()
        logging.info("Disconnecting MQTT client.")
        mqtt_client.disconnect()

# 1. Create an MCP server instance
mcp = FastMCP(
    "MQTT-MCP Bridge",
    instructions="This server acts as a bridge between the Model Context Protocol and an MQTT network.",
    host="0.0.0.0",
    port=8000,
    lifespan=mqtt_lifespan,
)

def create_tool_function(tool_name: str, command_topic: str, params: list) -> Coroutine:
    """
    Factory to create a fully dynamic async function for a registered tool.
    It builds a function with a signature that matches the parameters defined
    by the registering module.
    """
    
    param_defs = []
    for p in params:
        p_name = p.get("name")
        p_type = p.get("type", "Any") # Default to Any if not specified
        
        if not p_name:
            continue # Skip parameters without a name

        param_str = f"{p_name}: {p_type}"
        if "default" in p:
            default = p["default"]
            # Add quotes for string defaults
            param_str += f" = '{default}'" if isinstance(default, str) else f" = {default}"
        param_defs.append(param_str)

    # Add the context parameter, which is always present
    param_defs.append("ctx: Context | None = None")
    
    signature = ", ".join(param_defs)
    
    # The list of parameter names to be collected into the payload
    param_names = [p.get("name") for p in params if p.get("name")]

    # Create the function body
    func_body = f"""
async def dynamic_tool({signature}) -> str:
    logging.info(f"Async dynamic tool '{tool_name}' called.")

    if not ctx or not ctx.request_context.lifespan_context:
        msg = f"Tool '{tool_name}': Could not access lifespan context."
        logging.error(msg)
        return f"Error: {{msg}}"

    mqtt_client = ctx.request_context.lifespan_context.get("mqtt_client")
    if not mqtt_client:
        msg = f"Tool '{tool_name}': Could not access MQTT client from context."
        logging.error(msg)
        return f"Error: {{msg}}"

    correlation_id = str(uuid.uuid4())
    future = asyncio.get_running_loop().create_future()
    pending_futures[correlation_id] = future

    # Collect all defined parameters into a dictionary
    params_payload = {{}}
    for p_name in {param_names}:
        params_payload[p_name] = locals().get(p_name)

    command_payload = {{
        "correlation_id": correlation_id,
        "params": params_payload
    }}
    
    payload = json.dumps(command_payload)
    # Inject the command_topic value directly into the function's code
    mqtt_client.publish("{command_topic}", payload)
    logging.info(f"Tool '{tool_name}': Published command to '{command_topic}' with correlation_id: {{correlation_id}}")

    try:
        result = await asyncio.wait_for(future, timeout=10.0)
        logging.info(f"Tool '{tool_name}': Received result for {{correlation_id}}: {{result}}")
        return result
    except asyncio.TimeoutError:
        logging.error(f"Tool '{tool_name}': Timed out waiting for result for correlation_id: {{correlation_id}}")
        pending_futures.pop(correlation_id, None)
        return f"Error: Tool '{tool_name}' timed out."
    except Exception as e:
        logging.error(f"Tool '{tool_name}': An error occurred while waiting for future: {{e}}")
        return f"Error: An unexpected error occurred in tool '{tool_name}'."
"""
    
    # Define a local scope for exec to run in
    local_scope = {}
    # Execute the function definition
    exec(func_body, globals(), local_scope)
    
    # Retrieve the created function from the local scope
    created_func = local_scope['dynamic_tool']
    created_func.__name__ = tool_name
    
    logging.info(f"Successfully created dynamic function for tool '{tool_name}'")
    return created_func

def register_tool_from_definition(tool_def_payload: bytes):
    """Parses a tool definition and registers it with the MCP server."""
    logging.info(f"Attempting to register tool from payload: {tool_def_payload}")
    try:
        tool_def = json.loads(tool_def_payload)
        tool_name = tool_def.get("name")
        description = tool_def.get("description", "")
        parameters = tool_def.get("parameters", []) # Get parameters
        
        if not tool_name:
            logging.error(f"Registration failed: Tool definition missing 'name'. Payload: {tool_def_payload}")
            return

        command_topic = f"mcp/commands/{tool_name}"
        # Pass the parameters to the factory
        tool_func = create_tool_function(tool_name, command_topic, parameters)
        
        mcp.tool(name=tool_name, description=description)(tool_func)
        logging.info(f"Successfully registered tool: '{tool_name}'")

    except json.JSONDecodeError:
        logging.error(f"Registration failed: Failed to decode JSON from registration message: {tool_def_payload}")
    except Exception as e:
        logging.error(f"Registration failed: An unexpected error occurred: {e}")

async def process_registration_queue(registration_queue: queue.Queue):
    """Continuously checks a queue for new tool registrations and processes them."""
    logging.info("Starting tool registration queue processor.")
    while True:
        try:
            tool_def_payload = registration_queue.get_nowait()
            logging.info(f"Got tool definition from queue. Processing...")
            register_tool_from_definition(tool_def_payload)
        except queue.Empty:
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error in registration queue processor: {e}")

def main():
    """Entry point for the MCP server."""
    logging.info("Starting MCP server with SSE transport on port 8000...")
    mcp.settings.sse_path = "/mcp"
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
