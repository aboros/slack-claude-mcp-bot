import pytest
import json
from unittest.mock import MagicMock, patch
from claude_client import ClaudeClient, ClaudeResponse, ToolRequest
from mcp_manager import MCPManager
from slack_client import handle_mention, process_message, handle_claude_response

class TestIntegration:
    """Integration tests for Slack Bot components"""

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('slack_client.mcp_manager')
    @patch('slack_client.ClaudeClient')
    def test_slack_to_claude_to_mcp_flow(self, mock_claude_class, mock_mcp_manager, 
                                        mock_process_class, mock_popen, mock_config_file, 
                                        mock_anthropic_client, mock_psutil_process, mock_mcp_client):
        """Test the full flow from Slack message to Claude to MCP tool execution"""
        # Setup
        # Setup MCP Manager
        mock_process_class.return_value = mock_psutil_process
        mock_mcp_manager.get_available_tools.return_value = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "parameters": {
                    "param1": {"type": "string"}
                }
            }
        ]
        mock_mcp_manager.execute_tool.return_value = {"result": "Tool executed successfully"}
        
        # Setup Claude Client
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        # First response (tool use request)
        tool_request = ToolRequest(
            id="test-request-id",
            tool_name="test_tool",
            tool_params={"param1": "test_value"}
        )
        first_conversation = [{"role": "system", "content": "You are an assistant"}]
        first_response = ClaudeResponse(
            type="tool_use_request",
            content="I need to use a tool",
            tool_request=tool_request,
            conversation=first_conversation
        )
        
        # Second response (after tool execution)
        second_conversation = first_conversation + [
            {"role": "system", "content": "Tool result: success"}
        ]
        second_response = ClaudeResponse(
            type="final_answer",
            content="Here's your answer based on the tool result",
            conversation=second_conversation
        )
        
        # Configure mock Claude client
        mock_claude_instance.create_conversation.return_value = [
            {"role": "system", "content": "You are an assistant"}
        ]
        mock_claude_instance.send_message.return_value = first_response
        mock_claude_instance.send_tool_result.return_value = second_response
        
        # Setup for Slack
        client = MagicMock()
        say = MagicMock()
        event = {
            "text": "<@U12345> Use a tool to solve this problem",
            "channel": "C12345",
            "ts": "1609459200.123456",
            "user": "U67890"
        }
        
        # Execute - simulate the message flow
        with patch('uuid.uuid4', return_value='12345678-1234-5678-1234-567812345678'):
            handle_mention(client, event, say)
        
        # Verify
        # 1. Check that Claude was called to process the message
        mock_claude_instance.create_conversation.assert_called_once()
        mock_claude_instance.send_message.assert_called_once()
        
        # 2. Check that a tool approval request was sent to Slack
        client.chat_postMessage.assert_called_once()
        blocks = client.chat_postMessage.call_args[1]["blocks"]
        # Verify the blocks contain the tool name
        assert any("test_tool" in str(block) for block in blocks)
        
        # 3. Simulate tool approval and verify the full flow
        # Create a body that would be sent by Slack
        approval_body = {
            "actions": [{
                "value": json.dumps({
                    "conversation_id": "12345678-1234-5678-1234-567812345678",
                    "request_id": "test-request-id"
                })
            }],
            "channel": {"id": "C12345"},
            "message": {"ts": "1609459200.123456"},
            "message_thread_ts": "1609459200.000000"
        }
        
        # Handle the approval
        from slack_client import handle_tool_approval, conversation_store
        
        # Add the conversation to the store
        conversation_store["12345678-1234-5678-1234-567812345678"] = first_conversation
        
        # Execute the approval handler
        handle_tool_approval(client, approval_body, say)
        
        # Verify
        # 4. Check that the tool was executed
        mock_mcp_manager.execute_tool.assert_called_with("test-request-id")
        
        # 5. Check that Claude was called with tool result
        mock_claude_instance.send_tool_result.assert_called_with(
            first_conversation, "test-request-id", {"result": "Tool executed successfully"}
        )
        
        # 6. Check that final answer was posted to Slack
        say.assert_called_with(
            text="Here's your answer based on the tool result", 
            thread_ts=event["ts"]
        )

    @patch('slack_client.mcp_manager')
    @patch('claude_client.anthropic.Anthropic')
    def test_claude_to_slack_error_handling(self, mock_anthropic_class, mock_mcp_manager, mock_anthropic_client):
        """Test error handling when Claude API is unavailable"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")
        
        # Execute & Verify
        client = MagicMock()
        say = MagicMock()
        event = {
            "text": "<@U12345> Hello",
            "channel": "C12345",
            "ts": "1609459200.123456"
        }
        
        # The code should handle the exception
        handle_mention(client, event, say)
        
        # Verify an error message was sent
        say.assert_called_once()
        error_message = say.call_args[1].get("text", "")
        assert "error" in error_message.lower() or "failed" in error_message.lower()

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('slack_client.mcp_manager')
    @patch('slack_client.ClaudeClient')
    def test_tool_denial_flow(self, mock_claude_class, mock_mcp_manager, mock_process_class, 
                             mock_popen, mock_psutil_process):
        """Test the flow when a user denies a tool use request"""
        # Setup similar to previous test
        mock_process_class.return_value = mock_psutil_process
        
        # Setup Claude Client
        mock_claude_instance = MagicMock()
        mock_claude_class.return_value = mock_claude_instance
        
        # First response (tool use request)
        tool_request = ToolRequest(
            id="test-request-id",
            tool_name="test_tool",
            tool_params={"param1": "test_value"}
        )
        first_conversation = [{"role": "system", "content": "You are an assistant"}]
        first_response = ClaudeResponse(
            type="tool_use_request",
            content="I need to use a tool",
            tool_request=tool_request,
            conversation=first_conversation
        )
        
        # Denial response
        denial_response = ClaudeResponse(
            type="text",
            content="I understand you don't want me to use that tool. Let me try another approach.",
            conversation=first_conversation + [
                {"role": "system", "content": "Tool use request was denied"}
            ]
        )
        
        # Configure mock Claude client
        mock_claude_instance.create_conversation.return_value = first_conversation
        mock_claude_instance.send_message.return_value = first_response
        mock_claude_instance.notify_tool_denial.return_value = denial_response
        
        # Setup for Slack
        client = MagicMock()
        say = MagicMock()
        event = {
            "text": "<@U12345> Use a tool to solve this problem",
            "channel": "C12345",
            "ts": "1609459200.123456",
            "user": "U67890"
        }
        
        # Execute - simulate the message flow
        with patch('uuid.uuid4', return_value='12345678-1234-5678-1234-567812345678'):
            handle_mention(client, event, say)
        
        # Simulate tool denial
        from slack_client import handle_tool_denial, conversation_store
        
        # Add the conversation to the store
        conversation_store["12345678-1234-5678-1234-567812345678"] = first_conversation
        
        # Create a denial body
        denial_body = {
            "actions": [{
                "value": json.dumps({
                    "conversation_id": "12345678-1234-5678-1234-567812345678",
                    "request_id": "test-request-id"
                })
            }],
            "channel": {"id": "C12345"},
            "message": {"ts": "1609459200.123456"},
            "message_thread_ts": "1609459200.000000"
        }
        
        # Execute the denial handler
        handle_tool_denial(client, denial_body, say)
        
        # Verify
        # 1. Check that Claude was notified of the denial
        mock_claude_instance.notify_tool_denial.assert_called_with(
            first_conversation, "test-request-id"
        )
        
        # 2. Check that the message about denial was sent to Slack
        assert client.chat_update.called
        
        # 3. Check that Claude's response was posted to the thread
        say.assert_called_with(
            text="I understand you don't want me to use that tool. Let me try another approach.",
            thread_ts="1609459200.000000"
        ) 