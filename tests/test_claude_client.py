import pytest
import uuid
from unittest.mock import MagicMock, patch
from claude_client import ClaudeClient, ToolRequest, ClaudeResponse

class TestClaudeClient:
    """Test suite for the ClaudeClient class"""

    @patch('claude_client.anthropic.Anthropic')
    def test_initialization(self, mock_anthropic_class):
        """Test client initialization"""
        # Setup
        mock_anthropic_instance = MagicMock()
        mock_anthropic_class.return_value = mock_anthropic_instance
        
        # Execute
        client = ClaudeClient()
        
        # Verify
        assert client.client == mock_anthropic_instance
        mock_anthropic_class.assert_called_once()

    def test_create_conversation_no_tools(self):
        """Test conversation creation without tools"""
        # Setup
        client = ClaudeClient()
        
        # Execute
        conversation = client.create_conversation()
        
        # Verify
        assert len(conversation) == 1
        assert conversation[0]["role"] == "system"
        assert "You are a helpful assistant" in conversation[0]["content"]
        assert "Available tools" not in conversation[0]["content"]

    def test_create_conversation_with_tools(self):
        """Test conversation creation with tools"""
        # Setup
        client = ClaudeClient()
        tools = [
            {
                "name": "test_tool",
                "description": "A test tool"
            }
        ]
        
        # Execute
        conversation = client.create_conversation(tools=tools)
        
        # Verify
        assert len(conversation) == 1
        assert conversation[0]["role"] == "system"
        assert "You are a helpful assistant" in conversation[0]["content"]
        assert "Available tools" in conversation[0]["content"]

    def test_add_context(self):
        """Test adding context to a conversation"""
        # Setup
        client = ClaudeClient()
        conversation = client.create_conversation()
        messages = [
            {"role": "human", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        # Execute
        updated_conversation = client.add_context(conversation, messages)
        
        # Verify
        assert len(updated_conversation) == 3
        assert updated_conversation[0] == conversation[0]  # System message preserved
        assert updated_conversation[1:] == messages

    @patch('claude_client.anthropic.Anthropic')
    def test_send_message_text_response(self, mock_anthropic_class, mock_anthropic_client):
        """Test sending a message and getting a text response"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value.content[0].text = "This is a simple text response"
        
        client = ClaudeClient()
        conversation = client.create_conversation()
        message = "Hello Claude"
        
        # Execute
        response = client.send_message(conversation, message)
        
        # Verify
        assert isinstance(response, ClaudeResponse)
        assert response.type == "text"
        assert response.content == "This is a simple text response"
        assert response.tool_request is None
        assert len(response.conversation) == 3  # system + user + assistant
        mock_anthropic_client.messages.create.assert_called_once()

    @patch('claude_client.anthropic.Anthropic')
    @patch('uuid.uuid4')
    def test_send_message_tool_use_request(self, mock_uuid, mock_anthropic_class, mock_anthropic_client):
        """Test sending a message and getting a tool use request"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value.content[0].text = "I need to use <tool_use>test_tool</tool_use>"
        
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        
        client = ClaudeClient()
        conversation = client.create_conversation()
        message = "Use a tool"
        
        # Execute
        response = client.send_message(conversation, message)
        
        # Verify
        assert isinstance(response, ClaudeResponse)
        assert response.type == "tool_use_request"
        assert "<tool_use>" in response.content
        assert response.tool_request is not None
        assert response.tool_request.id == "12345678-1234-5678-1234-567812345678"
        assert len(response.conversation) == 3  # system + user + assistant

    @patch('claude_client.anthropic.Anthropic')
    def test_send_message_final_answer(self, mock_anthropic_class, mock_anthropic_client):
        """Test sending a message and getting a final answer"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value.content[0].text = "<final_answer>The final answer</final_answer>"
        
        client = ClaudeClient()
        conversation = client.create_conversation()
        message = "What's the answer?"
        
        # Execute
        response = client.send_message(conversation, message)
        
        # Verify
        assert isinstance(response, ClaudeResponse)
        assert response.type == "final_answer"
        assert response.content == "The final answer"
        assert response.tool_request is None
        assert len(response.conversation) == 3  # system + user + assistant

    @patch('claude_client.anthropic.Anthropic')
    def test_send_tool_result(self, mock_anthropic_class, mock_anthropic_client):
        """Test sending a tool result back to Claude"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value.content[0].text = "Thanks for the tool result"
        
        client = ClaudeClient()
        conversation = client.create_conversation()
        request_id = "test-request-id"
        tool_result = {"result": "success", "data": "tool output"}
        
        # Execute
        response = client.send_tool_result(conversation, request_id, tool_result)
        
        # Verify
        assert isinstance(response, ClaudeResponse)
        assert response.type == "text"
        assert response.content == "Thanks for the tool result"
        assert len(response.conversation) == 3  # system + tool result + assistant
        assert response.conversation[1]["role"] == "system"
        assert "Tool result" in response.conversation[1]["content"]

    @patch('claude_client.anthropic.Anthropic')
    def test_notify_tool_denial(self, mock_anthropic_class, mock_anthropic_client):
        """Test notifying Claude of tool denial"""
        # Setup
        mock_anthropic_class.return_value = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value.content[0].text = "I understand the tool was denied"
        
        client = ClaudeClient()
        conversation = client.create_conversation()
        request_id = "test-request-id"
        
        # Execute
        response = client.notify_tool_denial(conversation, request_id)
        
        # Verify
        assert isinstance(response, ClaudeResponse)
        assert response.type == "text"
        assert response.content == "I understand the tool was denied"
        assert len(response.conversation) == 3  # system + denial notification + assistant
        assert response.conversation[1]["role"] == "system"
        assert "denied" in response.conversation[1]["content"] 