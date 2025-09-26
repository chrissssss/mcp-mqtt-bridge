# MCP-MQTT Bridge

This project implements a bridge between the Model Context Protocol (MCP) and MQTT. It allows external clients (e.g., LLM UIs) to interact with a set of tools that are dynamically discovered and exposed by the MCP server. The core business logic resides in independent modules that communicate with the MCP server via an MQTT broker.

## Architecture

The system consists of three main components:

1.  **MCP Server:** A Python application that exposes an HTTP-based MCP endpoint. It acts as a gateway and dynamically discovers tools at runtime.
2.  **MQTT Broker:** A Mosquitto instance that serves as the central message bus for internal communication.
3.  **Modules:** Independent Python applications that perform specific tasks. On startup, they register their tools with the MCP server by publishing a message to a specific MQTT topic.

For a more detailed explanation of the architecture, please see [ARCHITECTURE.md](ARCHITECTURE.md).

## Getting Started

### Prerequisites

*   Docker
*   Docker Compose

### Running the Application

1.  Clone the repository:
    ```sh
    git clone https://github.com/chrissssss/mcp-mqtt-bridge.git
    cd mcp-mqtt-bridge
    ```

2.  Start the application using Docker Compose:
    ```sh
    docker-compose up -d
    ```

This will start the following services:
*   `mqtt-broker`: The Mosquitto MQTT broker.
*   `mcp-server`: The MCP server.
*   `hello-module`: A sample module that provides a "hello" tool.

## Usage

Once the application is running, you can interact with the MCP server. The server exposes the available tools, which are dynamically registered by the modules.

For example, the `hello-module` registers a `hello` tool. You can call this tool by sending a request to the MCP server's endpoint.

## Contributing

Contributions are welcome! Please read the [contribution guidelines](CONTRIBUTING.md) before submitting a pull request.
