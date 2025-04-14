# Slack Bot with Claude Integration and MCP Tools

## Overview

This document outlines the app flow and function structure for a Slack bot that integrates with Claude API and Model Context Protocol (MCP) servers for tool execution.

The flow is triggered when a user mentions the bot in a Slack channel or thread. The bot processes the message (including thread history if applicable), calls the Claude API, and handles different response types including text, tool use requests, and final answers.

## App Flow

1. **Trigger**: User mentions bot in Slack channel/thread
2. **Message Processing**:
   - Bot captures the mention event via `handle_mention()`
   - If in a thread, bot retrieves the thread history via `get_thread_history()`
   - `process_message()` creates a new Claude conversation with available tools

3. **Claude Interaction**:
   - Bot sends the user message to Claude via `send_message()`
   - Claude responds with one of three response types:
     - **Text Response**: Bot directly posts to Slack
     - **Tool Use Request**: Bot requests user approval with interactive buttons
     - **Final Answer**: Bot posts to the thread

4. **Tool Use Flow**:
   - **If Approved**:
     - Bot executes the tool via MCP (`execute_tool()`)
     - Bot sends the tool result back to Claude (`send_tool_result()`)
     - Bot handles Claude's response to the tool result
   - **If Denied**:
     - Bot informs Claude of the denial (`notify_tool_denial()`)
     - Bot handles Claude's response to the denial

5. **Completion**:
   - Process continues until Claude provides a final answer
   - Bot posts the final answer to the Slack thread

## MCP Integration

The application uses the [Model Context Protocol](https://modelcontextprotocol.io/quickstart/client#python) SDK to:

- Load tool configurations from `mcp.config.json`
- Launch configured MCP servers at startup
- Provide Claude with a list of available tools
- Execute tool requests as approved by users

This design keeps the application stateless, loading conversation context from Slack when needed and managing tool execution through MCP servers.

## App Structure

```
slack_bot/
├── main.py                   # Entry point
├── slack_client.py           # Slack API interactions
├── claude_client.py          # Claude API interactions
├── mcp_manager.py            # MCP server management
├── utils.py                  # Helper functions
└── mcp.config.json           # MCP configuration
```

## Function Mapping

### main.py

```python
def main():
    # Initialize MCP servers from config
    mcp_manager = MCPManager("mcp.config.json")
    
    # Initialize slack bolt app
    app = App(token=SLACK_BOT_TOKEN)
    
    # Register event handlers
    app.event("app_mention", handle_mention)
    app.action("approve_tool_use", handle_tool_approval)
    app.action("deny_tool_use", handle_tool_denial)
    
    # Start the app
    app.start()
```

### slack_client.py

```python
def handle_mention(client, event, say):
    """Handler for when bot is mentioned in a channel"""
    # Extract user message
    user_message = event["text"]
    
    # Check if mention is in a thread
    if "thread_ts" in event:
        # Load thread history
        thread_history = get_thread_history(client, event["channel"], event["thread_ts"])
        # Process with thread context
        process_message(client, event, say, user_message, thread_history)
    else:
        # Process without thread context
        process_message(client, event, say, user_message)

def get_thread_history(client, channel, thread_ts):
    """Retrieve all messages from a thread"""
    # Call Slack API to get thread replies
    result = client.conversations_replies(channel=channel, ts=thread_ts)
    # Format messages for Claude context
    return format_messages_for_claude(result["messages"])

def process_message(client, event, say, user_message, thread_history=None):
    """Process user message and handle Claude interaction"""
    # Initialize Claude client
    claude = ClaudeClient()
    
    # Get available tools from MCP manager
    tools = mcp_manager.get_available_tools()
    
    # Create conversation with Claude
    conversation_id = claude.create_conversation(tools=tools)
    
    # Add thread history if available
    if thread_history:
        claude.add_context(conversation_id, thread_history)
    
    # Send user message to Claude
    response = claude.send_message(conversation_id, user_message)
    
    # Handle Claude's response
    handle_claude_response(client, event, say, claude, conversation_id, response)

def handle_claude_response(client, event, say, claude, conversation_id, response):
    """Handle different types of responses from Claude"""
    if response.type == "text":
        # Simply post Claude's text response to Slack
        post_message(say, response.content, event)
    elif response.type == "tool_use_request":
        # Request user approval for tool use
        request_tool_approval(client, event, say, claude, conversation_id, response.tool_request)
    elif response.type == "final_answer":
        # Post final answer to thread
        post_message(say, response.content, event)

def request_tool_approval(client, event, say, claude, conversation_id, tool_request):
    """Request user approval for tool use"""
    # Create interactive message with approve/deny buttons
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": f"Claude wants to use tool: `{tool_request.tool_name}`"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"With parameters: ```{tool_request.tool_params}```"}},
        {"type": "actions", "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "Approve"}, 
             "value": json.dumps({"convo_id": conversation_id, "request_id": tool_request.id}),
             "action_id": "approve_tool_use"},
            {"type": "button", "text": {"type": "plain_text", "text": "Deny"}, 
             "value": json.dumps({"convo_id": conversation_id, "request_id": tool_request.id}),
             "action_id": "deny_tool_use"}
        ]}
    ]
    
    # Post message with buttons
    client.chat_postMessage(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]), blocks=blocks)

def handle_tool_approval(client, body, say):
    """Handle user approval of tool use"""
    # Parse payload value for conversation_id and request_id
    payload = json.loads(body["actions"][0]["value"])
    conversation_id = payload["convo_id"]
    request_id = payload["request_id"]
    
    # Update message to show approval
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Tool use approved. Processing...",
        blocks=[]
    )
    
    # Execute tool via MCP
    tool_result = mcp_manager.execute_tool(request_id)
    
    # Send tool result back to Claude
    claude = ClaudeClient()
    response = claude.send_tool_result(conversation_id, request_id, tool_result)
    
    # Handle Claude's response to the tool result
    event = {"channel": body["channel"]["id"], "ts": body["message"]["thread_ts"]}
    handle_claude_response(client, event, say, claude, conversation_id, response)

def handle_tool_denial(client, body, say):
    """Handle user denial of tool use"""
    # Parse payload value for conversation_id and request_id
    payload = json.loads(body["actions"][0]["value"])
    conversation_id = payload["convo_id"]
    request_id = payload["request_id"]
    
    # Update message to show denial
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Tool use denied.",
        blocks=[]
    )
    
    # Inform Claude that tool use was denied
    claude = ClaudeClient()
    response = claude.notify_tool_denial(conversation_id, request_id)
    
    # Handle Claude's response to the denial
    event = {"channel": body["channel"]["id"], "ts": body["message"]["thread_ts"]}
    handle_claude_response(client, event, say, claude, conversation_id, response)

def post_message(say, content, event):
    """Post message to Slack channel or thread"""
    if "thread_ts" in event:
        say(text=content, thread_ts=event["thread_ts"])
    else:
        say(text=content)
```

### claude_client.py

```python
class ClaudeClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    
    def create_conversation(self, tools=None):
        """Create a new Claude conversation with available tools"""
        # Create a message thread with Claude
        return str(uuid.uuid4())  # Simple UUID for demo, would be Claude's session ID
    
    def add_context(self, conversation_id, messages):
        """Add conversation context from thread history"""
        # Format and add messages to Claude's context
        pass
    
    def send_message(self, conversation_id, message):
        """Send message to Claude and get response"""
        # Call Claude API with message
        # Return response object with type (text, tool_use_request, final_answer)
        pass
    
    def send_tool_result(self, conversation_id, request_id, tool_result):
        """Send tool execution result back to Claude"""
        # Send tool result to Claude
        # Return Claude's response
        pass
    
    def notify_tool_denial(self, conversation_id, request_id):
        """Notify Claude that tool use was denied"""
        # Tell Claude the tool use was denied
        # Return Claude's response
        pass
```

### mcp_manager.py

```python
class MCPManager:
    def __init__(self, config_path):
        """Initialize MCP servers from config"""
        # Load configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)
        
        # Start MCP servers
        self.start_mcp_servers()
        
        # Initialize MCP client
        self.client = MCPClient()
    
    def start_mcp_servers(self):
        """Start all configured MCP servers"""
        # Import MCP SDK
        from mcp import MCPServer
        
        # Start each server based on config
        for server_config in self.config["servers"]:
            # Launch server with specified configuration
            pass
    
    def get_available_tools(self):
        """Get list of available tools from MCP servers"""
        # Query MCP client for available tools
        return self.client.list_tools()
    
    def execute_tool(self, request_id):
        """Execute tool via MCP"""
        # Use MCP client to execute the tool
        return self.client.execute_tool(request_id)
```
