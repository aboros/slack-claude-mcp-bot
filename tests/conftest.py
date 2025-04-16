import pytest
import json
import os
import sys
from unittest.mock import MagicMock, patch
from tests.mock_mcp import Client, start_server

# Add mock_mcp module to path for patching
@pytest.fixture(autouse=True)
def patch_mcp():
    """Patch the mcp module to use our mock instead"""
    with patch.dict(sys.modules, {'mcp': MagicMock()}):
        sys.modules['mcp'].Client = Client
        sys.modules['mcp'].start_server = start_server
        yield

@pytest.fixture
def mock_config():
    """Sample MCP configuration for testing"""
    return {
        "servers": [
            {
                "name": "test-server-1",
                "command": "python",
                "args": ["-m", "http.server", "8000"]
            },
            {
                "name": "test-server-2",
                "command": "echo",
                "args": ["test"]
            }
        ]
    }

@pytest.fixture
def mock_config_file(tmp_path, mock_config):
    """Create a temporary MCP config file for testing"""
    config_file = tmp_path / "test_mcp.config.json"
    with open(config_file, 'w') as f:
        json.dump(mock_config, f)
    return str(config_file)

@pytest.fixture
def mock_anthropic_client():
    """Mock for the Anthropic API client"""
    mock_client = MagicMock()
    mock_messages = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text="This is a mock response from Claude")]
    )
    mock_client.messages = mock_messages
    return mock_client

@pytest.fixture
def mock_slack_client():
    """Mock for Slack client with common methods"""
    mock_client = MagicMock()
    mock_client.conversations_replies.return_value = {
        "messages": [
            {"text": "Hello", "user": "U12345"},
            {"text": "Hi there", "bot_id": "B12345"}
        ]
    }
    return mock_client

@pytest.fixture
def mock_psutil_process():
    """Mock for psutil.Process with common methods"""
    mock_process = MagicMock()
    mock_process.is_running.return_value = True
    mock_process.status.return_value = "running"
    mock_process.pid = 12345
    return mock_process

@pytest.fixture
def mock_mcp_client():
    """Mock for MCP client"""
    mock_client = MagicMock()
    mock_client.list_tools.return_value = [
        {
            "name": "test_tool",
            "description": "A test tool for testing",
            "parameters": {
                "param1": {"type": "string"},
                "param2": {"type": "integer"}
            }
        }
    ]
    mock_client.execute_tool.return_value = {"result": "Tool executed successfully"}
    return mock_client 