import logging
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 1. Create an MCP server instance
mcp = FastMCP(
    "MQTT-MCP Bridge",
    instructions="This server acts as a bridge between the Model Context Protocol and an MQTT network.",
    host="0.0.0.0",
    port=8000
)

# 2. Add a simple tool for initial testing
@mcp.tool()
def hello(name: str = "World") -> str:
    """A simple tool to return a greeting."""
    logging.info(f"Tool 'hello' called with name: {name}")
    return f"Hello, {name}!"

def main():
    """Entry point for the MCP server."""
    logging.info("Starting MCP server with SSE transport on port 8000...")
    # Set the SSE path explicitly to match client configuration
    mcp.settings.sse_path = "/mcp"
    mcp.run(transport="sse")

if __name__ == "__main__":
    main()
