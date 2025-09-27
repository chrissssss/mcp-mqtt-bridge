import pytest
from hello_module.hello_module import on_connect, on_message
from unittest.mock import Mock

def test_on_connect():
    # Mock MQTT client and userdata
    client = Mock()
    userdata = None
    flags = 0
    reason_code = 0
    properties = None

    on_connect(client, userdata, flags, reason_code, properties)
    assert client.subscribe.called_once_with("mcp/commands/hello")
    assert client.publish.called_once_with("mcp/register", Mock())

def test_on_message():
    # Mock MQTT client, userdata, and message
    client = Mock()
    userdata = None
    msg = Mock()

    on_message(client, userdata, msg)
    assert client.publish.called_once_with("mcp/results/hello", Mock())

def test_on_connect_failure():
    # Mock MQTT client and userdata
    client = Mock()
    userdata = None
    flags = 0
    reason_code = 1
    properties = None

    on_connect(client, userdata, flags, reason_code, properties)
    assert not client.subscribe.called
    assert not client.publish.called

def test_reconnect_logic():
    # Mock MQTT client and userdata
    client = Mock()
    userdata = None
    flags = 0
    reason_code = 0
    properties = None

    client.connect.side_effect = [Exception("Mocked connection exception"), None]
    on_connect(client, userdata, flags, reason_code, properties)
    assert client.subscribe.called_once_with("mcp/commands/hello")
    assert client.publish.called_once_with("mcp/register", Mock())

def test_on_message_no_payload():
    # Mock MQTT client, userdata, and message
    client = Mock()
    userdata = None
    msg = Mock()
    msg.payload = None

    on_message(client, userdata, msg)
    assert not client.publish.called
