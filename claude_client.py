import os
import uuid
import anthropic
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Load environment variables
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")

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

class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        self.conversations = {}  # Store conversation messages
    
    def create_conversation(self, tools=None):
        """Create a new Claude conversation with available tools"""
        conversation_id = str(uuid.uuid4())
        
        # Initialize conversation with system message
        self.conversations[conversation_id] = [{
            "role": "system",
            "content": "You are a helpful assistant integrated with Slack. You can use tools when necessary."
        }]
        
        # Store tools configuration for this conversation
        if tools:
            self.conversations[conversation_id][0]["content"] += "\nAvailable tools: " + str(tools)
        
        return conversation_id
    
    def add_context(self, conversation_id, messages):
        """Add conversation context from thread history"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        # Add messages to conversation history
        # Skip the system message (index 0)
        self.conversations[conversation_id] = self.conversations[conversation_id][:1] + messages
    
    def send_message(self, conversation_id, message):
        """Send message to Claude and get response"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        # Add user message to conversation
        self.conversations[conversation_id].append({
            "role": "human",
            "content": message
        })
        
        # Call Claude API with the full conversation
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=self.conversations[conversation_id],
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        self.conversations[conversation_id].append({
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
                tool_request=tool_request
            )
        
        # Check if it's a final answer
        if "<final_answer>" in response_text:
            return ClaudeResponse(
                type="final_answer",
                content=response_text.replace("<final_answer>", "").replace("</final_answer>", "")
            )
        
        # Default to text response
        return ClaudeResponse(
            type="text",
            content=response_text
        )
    
    def send_tool_result(self, conversation_id, request_id, tool_result):
        """Send tool execution result back to Claude"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        # Add tool result as a system message
        self.conversations[conversation_id].append({
            "role": "system",
            "content": f"Tool result for request {request_id}: {tool_result}"
        })
        
        # Call Claude API for next response
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=self.conversations[conversation_id],
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response (similar to send_message)
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        self.conversations[conversation_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        # Similar logic to send_message for determining response type
        # This is simplified - actual implementation would depend on Claude's API
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
                tool_request=tool_request
            )
        
        if "<final_answer>" in response_text:
            return ClaudeResponse(
                type="final_answer",
                content=response_text.replace("<final_answer>", "").replace("</final_answer>", "")
            )
        
        return ClaudeResponse(
            type="text",
            content=response_text
        )
    
    def notify_tool_denial(self, conversation_id, request_id):
        """Notify Claude that tool use was denied"""
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} does not exist")
        
        # Add tool denial as a system message
        self.conversations[conversation_id].append({
            "role": "system",
            "content": f"Tool use request {request_id} was denied by the user."
        })
        
        # Call Claude API for next response
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            messages=self.conversations[conversation_id],
            max_tokens=1024,
            system="You are a helpful assistant integrated with Slack.",
        )
        
        # Process response (similar to send_message)
        response_text = response.content[0].text
        
        # Add assistant response to conversation
        self.conversations[conversation_id].append({
            "role": "assistant",
            "content": response_text
        })
        
        # Default to text response as tool was denied
        return ClaudeResponse(
            type="text",
            content=response_text
        )
