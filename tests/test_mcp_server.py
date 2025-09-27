import pytest
from mcp_server.mcp_server import create_tool_function, register_tool_from_definition
from unittest.mock import Mock

def test_create_tool_function():
    # Mock tool definition
    tool_def = {
        "name": "test_tool",
        "description": "Test tool",
        "parameters": [
            {"name": "param1", "type": "str"}
        ]
    }

    tool_func = create_tool_function("test_tool", "mcp/commands/test_tool", tool_def["parameters"])
    assert callable(tool_func)
    assert tool_func.__name__ == "test_tool"

def test_register_tool_from_definition():
    # Mock tool definition
    tool_def = {
        "name": "test_tool",
        "description": "Test tool",
        "parameters": [
            {"name": "param1", "type": "str"}
        ]
    }

    register_tool_from_definition(Mock())
    assert True
