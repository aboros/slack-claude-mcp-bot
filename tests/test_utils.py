import pytest
import json
import os
from unittest.mock import patch, mock_open
from utils import (
    load_json_file, format_tool_parameters, parse_slack_message,
    format_message_for_claude, validate_mcp_config
)

class TestUtils:
    """Test suite for utility functions"""

    def test_load_json_file(self, tmp_path):
        """Test loading a valid JSON file"""
        # Setup
        test_data = {"key": "value", "nested": {"key2": "value2"}}
        json_file = tmp_path / "test.json"
        with open(json_file, 'w') as f:
            json.dump(test_data, f)
        
        # Execute
        result = load_json_file(str(json_file))
        
        # Verify
        assert result == test_data

    def test_load_json_file_not_found(self):
        """Test loading a non-existent JSON file"""
        # Setup
        non_existent_file = "/path/to/nonexistent/file.json"
        
        # Execute & Verify
        with pytest.raises(FileNotFoundError):
            load_json_file(non_existent_file)

    def test_load_json_file_invalid_json(self, tmp_path):
        """Test loading an invalid JSON file"""
        # Setup
        invalid_json_file = tmp_path / "invalid.json"
        with open(invalid_json_file, 'w') as f:
            f.write("This is not valid JSON")
        
        # Execute & Verify
        with pytest.raises(json.JSONDecodeError):
            load_json_file(str(invalid_json_file))

    def test_format_tool_parameters(self):
        """Test formatting tool parameters for display"""
        # Setup
        params = {
            "param1": "value1",
            "param2": 42,
            "param3": {"nested": "value"}
        }
        
        # Execute
        result = format_tool_parameters(params)
        
        # Verify
        # Check that the result is a valid JSON string
        parsed_result = json.loads(result)
        assert parsed_result == params
        # Check that it's properly indented
        assert "  " in result  # Check for indentation

    def test_parse_slack_message_with_bot_mention(self):
        """Test parsing a Slack message with a bot mention"""
        # Setup
        message = "<@U12345> Hello bot, how are you?"
        bot_user_id = "U12345"
        
        # Execute
        result = parse_slack_message(message, bot_user_id)
        
        # Verify
        assert result == "Hello bot, how are you?"

    def test_parse_slack_message_without_bot_mention(self):
        """Test parsing a Slack message without a bot mention"""
        # Setup
        message = "Hello bot, how are you?"
        bot_user_id = "U12345"
        
        # Execute
        result = parse_slack_message(message, bot_user_id)
        
        # Verify
        assert result == message

    def test_parse_slack_message_no_bot_id(self):
        """Test parsing a Slack message without specifying bot ID"""
        # Setup
        message = "<@U12345> Hello bot, how are you?"
        
        # Execute
        result = parse_slack_message(message)
        
        # Verify
        assert result == message  # Message should remain unchanged

    def test_format_message_for_claude(self):
        """Test formatting Slack messages for Claude API format"""
        # Setup
        messages = [
            {"text": "Hello bot", "user": "U12345"},
            {"text": "Hi there", "bot_id": "B12345"},
            {"text": "How are you?", "user": "U12345"}
        ]
        
        # Execute
        result = format_message_for_claude(messages)
        
        # Verify
        assert len(result) == 2  # Bot message should be skipped
        assert result[0]["role"] == "human"
        assert result[0]["content"] == "Hello bot"
        assert result[1]["role"] == "human"
        assert result[1]["content"] == "How are you?"

    def test_validate_mcp_config_valid(self):
        """Test validating a valid MCP configuration"""
        # Setup
        valid_config = {
            "servers": [
                {
                    "name": "server1",
                    "command": "python",
                    "args": ["-m", "http.server", "8000"]
                },
                {
                    "name": "server2",
                    "module": "test_module"
                }
            ]
        }
        
        # Execute
        result = validate_mcp_config(valid_config)
        
        # Verify
        assert result is True

    def test_validate_mcp_config_missing_servers(self):
        """Test validating a config missing the 'servers' section"""
        # Setup
        invalid_config = {
            "other_section": []
        }
        
        # Execute
        result = validate_mcp_config(invalid_config)
        
        # Verify
        assert result is False

    def test_validate_mcp_config_missing_name(self):
        """Test validating a config with a server missing 'name'"""
        # Setup
        invalid_config = {
            "servers": [
                {
                    "command": "python",
                    "args": ["-m", "http.server", "8000"]
                }
            ]
        }
        
        # Execute
        result = validate_mcp_config(invalid_config)
        
        # Verify
        assert result is False

    def test_validate_mcp_config_missing_command_and_module(self):
        """Test validating a config with a server missing both 'command' and 'module'"""
        # Setup
        invalid_config = {
            "servers": [
                {
                    "name": "server1",
                    "args": ["-m", "http.server", "8000"]
                }
            ]
        }
        
        # Execute
        result = validate_mcp_config(invalid_config)
        
        # Verify
        assert result is False 