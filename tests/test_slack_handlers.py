import pytest
import json
import uuid
import sys
from unittest.mock import MagicMock, patch, call
from slack_client import (
    handle_mention, get_thread_history, format_messages_for_claude, 
    process_message, handle_claude_response, request_tool_approval,
    handle_tool_approval, handle_tool_denial, post_message,
    conversation_store
)
from claude_client import ClaudeResponse, ToolRequest

class TestSlackHandlers:
    """Test suite for Slack client handlers"""

    def test_format_messages_for_claude(self):
        """Test formatting Slack messages for Claude"""
        # Setup
        messages = [
            {"text": "Hello bot", "user": "U12345"},
            {"text": "Hi human", "bot_id": "B12345"},
            {"text": "How can I help?", "user": "U67890"}
        ]
        
        # Execute
        formatted = format_messages_for_claude(messages)
        
        # Verify
        assert len(formatted) == 2  # Bot message should be skipped
        assert formatted[0]["role"] == "human"
        assert formatted[0]["content"] == "Hello bot"
        assert formatted[1]["role"] == "human"
        assert formatted[1]["content"] == "How can I help?"

    @patch('slack_client.get_thread_history')
    @patch('slack_client.process_message')
    def test_handle_mention_in_thread(self, mock_process_message, mock_get_thread_history):
        """Test handling mention in a thread"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        event = {
            "text": "<@U12345> Hello bot",
            "channel": "C12345",
            "thread_ts": "1609459200.123456"
        }
        
        mock_thread_history = [{"role": "human", "content": "previous message"}]
        mock_get_thread_history.return_value = mock_thread_history
        
        # Execute
        handle_mention(client, event, say)
        
        # Verify
        mock_get_thread_history.assert_called_with(client, event["channel"], event["thread_ts"])
        mock_process_message.assert_called_with(client, event, say, "Hello bot", mock_thread_history)

    @patch('slack_client.process_message')
    def test_handle_mention_not_in_thread(self, mock_process_message):
        """Test handling mention not in a thread"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        event = {
            "text": "<@U12345> Hello bot",
            "channel": "C12345"
        }
        
        # Execute
        handle_mention(client, event, say)
        
        # Verify
        mock_process_message.assert_called_with(client, event, say, "Hello bot")

    def test_get_thread_history(self, mock_slack_client):
        """Test retrieving thread history"""
        # Setup
        channel = "C12345"
        thread_ts = "1609459200.123456"
        
        # Execute
        result = get_thread_history(mock_slack_client, channel, thread_ts)
        
        # Verify
        mock_slack_client.conversations_replies.assert_called_with(channel=channel, ts=thread_ts)
        assert len(result) == 1  # Bot message should be filtered out
        assert result[0]["role"] == "human"
        assert result[0]["content"] == "Hello"

    @patch('slack_client.ClaudeClient')
    def test_process_message_no_thread_history(self, mock_claude_class):
        """Test processing a message without thread history"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        user_message = "Hello bot"
        
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        mock_tools = [{"name": "test_tool"}]
        mock_mcp_manager = MagicMock()
        mock_mcp_manager.get_available_tools.return_value = mock_tools
        
        mock_conversation = [{"role": "system", "content": "You are a helpful assistant"}]
        mock_claude_instance.create_conversation.return_value = mock_conversation
        
        mock_response = MagicMock(
            type="text",
            content="Hello human",
            tool_request=None,
            conversation=mock_conversation + [
                {"role": "human", "content": user_message},
                {"role": "assistant", "content": "Hello human"}
            ]
        )
        mock_claude_instance.send_message.return_value = mock_response
        
        # Create a mock module for main
        mock_main = MagicMock()
        mock_main.mcp_manager = mock_mcp_manager
        
        # Execute
        with patch.dict(sys.modules, {'main': mock_main}):
            process_message(client, event, say, user_message)
        
        # Verify
        mock_mcp_manager.get_available_tools.assert_called_once()
        mock_claude_instance.create_conversation.assert_called_with(tools=mock_tools)
        mock_claude_instance.send_message.assert_called_with(mock_conversation, user_message)

    @patch('slack_client.ClaudeClient')
    @patch('slack_client.handle_claude_response')
    def test_process_message_with_thread_history(self, mock_handle_response, mock_claude_class):
        """Test processing a message with thread history"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        user_message = "Hello bot"
        thread_history = [{"role": "human", "content": "previous message"}]
        
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        mock_conversation = [{"role": "system", "content": "You are a helpful assistant"}]
        mock_claude_instance.create_conversation.return_value = mock_conversation
        
        mock_conversation_with_context = mock_conversation + thread_history
        mock_claude_instance.add_context.return_value = mock_conversation_with_context
        
        mock_response = MagicMock()
        mock_claude_instance.send_message.return_value = mock_response
        
        # Execute
        process_message(client, event, say, user_message, thread_history)
        
        # Verify
        mock_claude_instance.create_conversation.assert_called_once()
        mock_claude_instance.add_context.assert_called_with(mock_conversation, thread_history)
        mock_claude_instance.send_message.assert_called_with(mock_conversation_with_context, user_message)
        mock_handle_response.assert_called_with(client, event, say, mock_claude_instance, mock_response)

    @patch('slack_client.post_message')
    def test_handle_claude_text_response(self, mock_post_message):
        """Test handling a text response from Claude"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        claude = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        
        response = ClaudeResponse(
            type="text",
            content="This is a text response",
            conversation=[{"role": "system", "content": "You are a helpful assistant"}]
        )
        
        # Execute
        handle_claude_response(client, event, say, claude, response)
        
        # Verify
        mock_post_message.assert_called_with(say, "This is a text response", event)

    @patch('slack_client.request_tool_approval')
    @patch('uuid.uuid4')
    def test_handle_claude_tool_use_request(self, mock_uuid, mock_request_approval):
        """Test handling a tool use request from Claude"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        claude = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        
        tool_request = ToolRequest(
            id="test-tool-request",
            tool_name="test_tool",
            tool_params={"param1": "value1"}
        )
        
        conversation = [{"role": "system", "content": "You are a helpful assistant"}]
        
        response = ClaudeResponse(
            type="tool_use_request",
            content="I need to use a tool",
            tool_request=tool_request,
            conversation=conversation
        )
        
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        
        # Execute
        handle_claude_response(client, event, say, claude, response)
        
        # Verify
        # Verify conversation was stored
        assert '12345678-1234-5678-1234-567812345678' in conversation_store
        assert conversation_store['12345678-1234-5678-1234-567812345678'] == conversation
        
        # Verify tool approval was requested
        mock_request_approval.assert_called_with(
            client, event, say, claude, '12345678-1234-5678-1234-567812345678', tool_request
        )

    @patch('slack_client.post_message')
    def test_handle_claude_final_answer(self, mock_post_message):
        """Test handling a final answer from Claude"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        claude = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        
        response = ClaudeResponse(
            type="final_answer",
            content="This is the final answer",
            conversation=[{"role": "system", "content": "You are a helpful assistant"}]
        )
        
        # Execute
        handle_claude_response(client, event, say, claude, response)
        
        # Verify
        mock_post_message.assert_called_with(say, "This is the final answer", event)

    def test_request_tool_approval(self):
        """Test requesting user approval for tool use"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        claude = MagicMock()
        event = {"channel": "C12345", "ts": "1609459200.123456"}
        conversation_id = "test-conversation-id"
        
        tool_request = ToolRequest(
            id="test-request-id",
            tool_name="test_tool",
            tool_params={"param1": "value1"}
        )
        
        # Execute
        request_tool_approval(client, event, say, claude, conversation_id, tool_request)
        
        # Verify
        client.chat_postMessage.assert_called_once()
        # Check that the call contains the expected parameters
        args, kwargs = client.chat_postMessage.call_args
        assert kwargs["channel"] == event["channel"]
        assert kwargs["thread_ts"] == event["ts"]
        assert "blocks" in kwargs
        
        # Check that blocks contain the tool name and parameters
        blocks = kwargs["blocks"]
        assert any("test_tool" in str(block) for block in blocks)
        assert any("param1" in str(block) for block in blocks)
        assert any("value1" in str(block) for block in blocks)

    @patch('slack_client.ClaudeClient')
    def test_handle_tool_approval(self, mock_claude_class):
        """Test handling tool approval from user"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        body = {
            "actions": [{
                "value": json.dumps({
                    "conversation_id": "test-conversation-id",
                    "request_id": "test-request-id"
                })
            }],
            "channel": {"id": "C12345"},
            "message": {"ts": "1609459200.123456"},
            "message_thread_ts": "1609459200.000000"
        }
        
        # Add a test conversation to the store
        test_conversation = [{"role": "system", "content": "System message"}]
        conversation_store["test-conversation-id"] = test_conversation
        
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        mock_mcp_manager = MagicMock()
        tool_result = {"result": "Tool executed successfully"}
        mock_mcp_manager.execute_tool.return_value = tool_result
        
        mock_response = MagicMock()
        mock_claude_instance.send_tool_result.return_value = mock_response
        
        # Create a mock module for main
        mock_main = MagicMock()
        mock_main.mcp_manager = mock_mcp_manager
        
        # Execute
        with patch.dict(sys.modules, {'main': mock_main}):
            handle_tool_approval(client, body, say)
        
        # Verify
        # Check that the message was updated
        client.chat_update.assert_called_once()
        
        # Check that the tool was executed
        mock_mcp_manager.execute_tool.assert_called_with("test-request-id")
        
        # Check that the tool result was sent back to Claude
        mock_claude_instance.send_tool_result.assert_called_with(
            test_conversation, "test-request-id", tool_result
        )

    @patch('slack_client.ClaudeClient')
    @patch('slack_client.handle_claude_response')
    def test_handle_tool_denial(self, mock_handle_response, mock_claude_class):
        """Test handling tool denial from user"""
        # Setup
        client = MagicMock()
        say = MagicMock()
        body = {
            "actions": [{
                "value": json.dumps({
                    "conversation_id": "test-conversation-id",
                    "request_id": "test-request-id"
                })
            }],
            "channel": {"id": "C12345"},
            "message": {"ts": "1609459200.123456"},
            "message_thread_ts": "1609459200.000000"
        }
        
        # Add a test conversation to the store
        test_conversation = [{"role": "system", "content": "System message"}]
        conversation_store["test-conversation-id"] = test_conversation
        
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        mock_response = MagicMock()
        mock_claude_instance.notify_tool_denial.return_value = mock_response
        
        # Execute
        handle_tool_denial(client, body, say)
        
        # Verify
        # Check that the message was updated
        client.chat_update.assert_called_once()
        
        # Check that Claude was notified of the denial
        mock_claude_instance.notify_tool_denial.assert_called_with(
            test_conversation, "test-request-id"
        )
        
        # Check that the response was handled
        mock_handle_response.assert_called_once()

    def test_post_message_in_thread(self):
        """Test posting a message in a thread"""
        # Setup
        say = MagicMock()
        content = "Test message"
        event = {
            "channel": "C12345",
            "thread_ts": "1609459200.123456"
        }
        
        # Execute
        post_message(say, content, event)
        
        # Verify
        say.assert_called_with(text=content, thread_ts=event["thread_ts"])

    def test_post_message_not_in_thread(self):
        """Test posting a message not in a thread"""
        # Setup
        say = MagicMock()
        content = "Test message"
        event = {
            "channel": "C12345"
        }
        
        # Execute
        post_message(say, content, event)
        
        # Verify
        say.assert_called_with(text=content) 