import os
import uuid
import anthropic
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

# Load environment variables
CLAUDE_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-latest")

@dataclass
class ToolRequest:
    id: str
    tool_name: str
    tool_params: Dict[str, Any]

@dataclass
class ClaudeResponse:
    type: str  # "text", "tool_use_request", or "final_answer"
    content: str
    tool_request: Optional[ToolRequest] = None
    conversation: List[Dict[str, Any]] = None

class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    
    def create_conversation(self, tools=None):
        """Create a new conversation with available tools and return the conversation history"""
        # Initialize conversation with system message
        conversation = [{
            "role": "system",
            "content": "You are a helpful assistant integrated with Slack. You can use tools when necessary."
        }]
        
        # Add tools configuration if provided
        if tools:
            conversation[0]["content"] += "\nAvailable tools: " + str(tools)
        
        return conversation
    
    def add_context(self, conversation, messages):
        """Add conversation context from thread history and return updated conversation"""
        # Create a new conversation list, preserving the system message
        updated_conversation = conversation[:1] + messages
        return updated_conversation
    
    def send_message(self, conversation, message):
        """Send message to Claude and get response along with updated conversation"""
        # Create a copy of the conversation to avoid modifying the original
        updated_conversation = conversation.copy()
        
        # Add user message to conversation
        updated_conversation.append({
            "role": "human",
            "content": message
        })
        
        # Call Claude API with the conversation
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=updated_conversation,
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        updated_conversation.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Check if response contains tool use request
        # This is simplified - actual tool use detection would depend on Claude's API
        if "<tool_use>" in response_text:
            # Parse tool use request - this is a simplified example
            # In practice, you'd extract this from Claude's structured response
            tool_name = "example_tool"
            tool_params = {"param1": "value1"}
            request_id = str(uuid.uuid4())
            
            tool_request = ToolRequest(
                id=request_id,
                tool_name=tool_name,
                tool_params=tool_params
            )
            
            return ClaudeResponse(
                type="tool_use_request",
                content=response_text,
                tool_request=tool_request,
                conversation=updated_conversation
            )
        
        # Check if it's a final answer
        if "<final_answer>" in response_text:
            return ClaudeResponse(
                type="final_answer",
                content=response_text.replace("<final_answer>", "").replace("</final_answer>", ""),
                conversation=updated_conversation
            )
        
        # Default to text response
        return ClaudeResponse(
            type="text",
            content=response_text,
            conversation=updated_conversation
        )
    
    def send_tool_result(self, conversation, request_id, tool_result):
        """Send tool execution result back to Claude"""
        # Create a copy of the conversation to avoid modifying the original
        updated_conversation = conversation.copy()
        
        # Add tool result as a system message
        updated_conversation.append({
            "role": "system",
            "content": f"Tool result for request {request_id}: {tool_result}"
        })
        
        # Call Claude API for next response
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=updated_conversation,
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        updated_conversation.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Similar logic to send_message for determining response type
        if "<tool_use>" in response_text:
            tool_name = "example_tool"
            tool_params = {"param1": "value1"}
            new_request_id = str(uuid.uuid4())
            
            tool_request = ToolRequest(
                id=new_request_id,
                tool_name=tool_name,
                tool_params=tool_params
            )
            
            return ClaudeResponse(
                type="tool_use_request",
                content=response_text,
                tool_request=tool_request,
                conversation=updated_conversation
            )
        
        if "<final_answer>" in response_text:
            return ClaudeResponse(
                type="final_answer",
                content=response_text.replace("<final_answer>", "").replace("</final_answer>", ""),
                conversation=updated_conversation
            )
        
        return ClaudeResponse(
            type="text",
            content=response_text,
            conversation=updated_conversation
        )
    
    def notify_tool_denial(self, conversation, request_id):
        """Notify Claude that tool use was denied"""
        # Create a copy of the conversation to avoid modifying the original
        updated_conversation = conversation.copy()
        
        # Add tool denial as a system message
        updated_conversation.append({
            "role": "system",
            "content": f"Tool use request {request_id} was denied by the user."
        })
        
        # Call Claude API for next response
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=updated_conversation,
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        updated_conversation.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Return text response as tool was denied
        return ClaudeResponse(
            type="text",
            content=response_text,
            conversation=updated_conversation
        )
