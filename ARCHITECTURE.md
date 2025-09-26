# Architecture and Feature Plan: MCP-MQTT Bridge

This document outlines the target architecture for integrating a Model Context Protocol (MCP) server into the existing MQTT-based application.

## 1. Target Architecture

The goal is to create a robust and decoupled system where an MCP server acts as the primary interface for external clients (e.g., LLM UIs), while the core business logic resides in independent modules that communicate via MQTT.

### Core Components:

1.  **MCP Server:** A single Python application that exposes an HTTP-based MCP endpoint. It does not contain any core business logic itself. It acts as a gateway or bridge.
2.  **MQTT Broker:** The central message bus for internal communication (already implemented with Mosquitto).
3.  **Modules:** Independent Python applications (e.g., the existing publisher, a new subscriber logic) that perform specific tasks.

### Communication Flow:

-   **Client -> MCP Server:** Standard MCP communication over HTTP(S). The client discovers and calls tools.
-   **MCP Server <-> Modules:** All communication happens via MQTT messages.

### Dynamic Tool Registration:

A key feature is that the MCP server does not have statically defined tools. Instead, it discovers them at runtime.

1.  **Module Startup:** When a module starts, it connects to the MQTT broker.
2.  **Registration:** The module publishes a message to a well-defined registration topic (e.g., `mcp/register`). This message contains a definition of the tool(s) the module provides (name, description, parameters).
3.  **Discovery:** The MCP server subscribes to the registration topic. Upon receiving a registration message, it dynamically adds the new tool to its list of available tools, making it accessible to MCP clients.
4.  **Execution:** When an MCP client calls a tool, the MCP server publishes a "command" message to a corresponding MQTT topic (e.g., `mcp/commands/my_tool`). The responsible module listens on this topic, executes the command with the provided arguments, and must publish a result to a corresponding result topic (e.g., `mcp/results/my_tool`) to complete the request-response cycle.

## 2. Implementation Plan (Incremental Steps)

We will approach this goal in a series of small, verifiable steps.

1.  **Step 1: Static MCP Server.**
    -   **Status: Completed**
    -   Create `mcp_server.py`.
    -   Implement a basic `FastMCP` server with a single, hard-coded "Hello World" tool.
    -   This step verifies that the MCP dependency is correctly installed and the server can be started.

2.  **Step 2: MQTT Anbindung des Servers (Server MQTT Connection).**
    -   **Status: Completed**
    -   Extend the `mcp_server.py` to connect to the MQTT broker on startup.

3.  **Step 3: Static Bridge (MCP -> MQTT).**
    -   **Status: Completed**
    -   Modify the hard-coded tool in the MCP server.
    -   When the tool is called, it should publish a simple message to a dedicated MQTT topic (e.g., `mcp/commands/hello`).
    -   Create a new, simple Python script that subscribes to this topic and logs the received message.
    -   This verifies the communication bridge from the MCP server to a module.

4.  **Step 4: Dynamic Registration.**
    -   **Status: Completed**
    -   Implement the dynamic registration logic as described in the target architecture.
    -   The module will send its tool definition on startup.
    -   The MCP server will listen and dynamically register the tool.

5.  **Step 5: Integration and Refinement.**
    -   **Status: Completed**
    -   Refactor the existing `publisher` and `subscriber` applications to function as modules within this new architecture.
    -   Flesh out the command-and-control message format. This has been implemented to include correlation IDs, enabling a full request-response cycle between the MCP server and the modules.
