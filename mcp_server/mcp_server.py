import logging
import paho.mqtt.client as mqtt
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from mcp.server.fastmcp import FastMCP, Context

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MQTT Configuration ---
MQTT_BROKER = "mqtt-broker"
MQTT_PORT = 1883
COMMAND_TOPIC = "mcp/commands/hello"

# --- Lifespan Management for MQTT Connection ---
@asynccontextmanager
async def mqtt_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manages the MQTT client's connection lifecycle."""
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logging.error(f"MQTT failed to connect: {reason_code}")
        else:
            logging.info("MQTT client connected successfully.")

    def on_disconnect(client, userdata, flags, reason_code, properties):
        logging.info("MQTT client disconnected.")

    # Create and configure the MQTT client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect

    logging.info(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start() # Start a background thread for the network loop

    try:
        # Yield the client so tools can use it
        yield {"mqtt_client": mqtt_client}
    finally:
        # Cleanup on shutdown
        logging.info("Stopping MQTT client loop.")
        mqtt_client.loop_stop()
        logging.info("Disconnecting MQTT client.")
        mqtt_client.disconnect()


# 1. Create an MCP server instance with the MQTT lifespan manager
mcp = FastMCP(
    "MQTT-MCP Bridge",
    instructions="This server acts as a bridge between the Model Context Protocol and an MQTT network.",
    host="0.0.0.0",
    port=8000,
    lifespan=mqtt_lifespan
)

# 2. Add a simple tool for initial testing
@mcp.tool()
def hello(name: str = "World", ctx: Context | None = None) -> str:
    """A simple tool that publishes a message via MQTT."""
    logging.info(f"Tool 'hello' called with name: {name}")

    if ctx and ctx.request_context.lifespan_context:
        mqtt_client = ctx.request_context.lifespan_context.get("mqtt_client")
        if mqtt_client:
            payload = f"Hello {name} from MCP!"
            mqtt_client.publish(COMMAND_TOPIC, payload)
            logging.info(f"Published to {COMMAND_TOPIC}: {payload}")
            return f"Successfully sent '{payload}' to the MQTT network."

    return "Error: Could not access MQTT client."

def main():
    """Entry point for the MCP server."""
    logging.info("Starting MCP server with SSE transport on port 8000...")
    # Set the SSE path explicitly to match client configuration
    mcp.settings.sse_path = "/mcp"
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
