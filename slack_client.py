import json
import uuid
from claude_client import ClaudeClient
from mcp_manager import MCPManager
from main import mcp_manager  # Import the global instance from main.py

# Remove redundant initialization
# mcp_manager = MCPManager("mcp.config.json")

# Temporary storage for conversation histories
# Maps conversation_id -> conversation
conversation_store = {}

def handle_mention(client, event, say):
    """Handler for when bot is mentioned in a channel"""
    # Extract user message - remove the bot mention
    user_message = event["text"].split(">", 1)[1].strip() if ">" in event["text"] else event["text"]
    
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

def format_messages_for_claude(messages):
    """Format slack messages for Claude's context"""
    formatted = []
    for msg in messages:
        # Skip bot's own messages to avoid confusion
        if msg.get("bot_id"):
            continue
            
        role = "human" if not msg.get("bot_id") else "assistant"
        formatted.append({
            "role": role,
            "content": msg["text"]
        })
    return formatted

def process_message(client, event, say, user_message, thread_history=None):
    """Process user message and handle Claude interaction"""
    # Initialize Claude client
    claude = ClaudeClient()
    
    # Get available tools from MCP manager
    tools = mcp_manager.get_available_tools()
    
    # Create conversation with Claude
    conversation = claude.create_conversation(tools=tools)
    
    # Add thread history if available
    if thread_history:
        conversation = claude.add_context(conversation, thread_history)
    
    # Send user message to Claude
    response = claude.send_message(conversation, user_message)
    
    # Handle Claude's response
    handle_claude_response(client, event, say, claude, response)

def handle_claude_response(client, event, say, claude, response):
    """Handle different types of responses from Claude"""
    conversation = response.conversation
    
    if response.type == "text":
        # Simply post Claude's text response to Slack
        post_message(say, response.content, event)
    elif response.type == "tool_use_request":
        # Store conversation in memory with a unique ID
        conversation_id = str(uuid.uuid4())
        conversation_store[conversation_id] = conversation
        
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
             "value": json.dumps({"conversation_id": conversation_id, "request_id": tool_request.id}),
             "action_id": "approve_tool_use"},
            {"type": "button", "text": {"type": "plain_text", "text": "Deny"}, 
             "value": json.dumps({"conversation_id": conversation_id, "request_id": tool_request.id}),
             "action_id": "deny_tool_use"}
        ]}
    ]
    
    # Post message with buttons
    client.chat_postMessage(channel=event["channel"], thread_ts=event.get("thread_ts", event["ts"]), blocks=blocks)

def handle_tool_approval(client, body, say):
    """Handle user approval of tool use"""
    # Parse payload value for conversation_id and request_id
    payload = json.loads(body["actions"][0]["value"])
    conversation_id = payload["conversation_id"]
    request_id = payload["request_id"]
    
    # Retrieve conversation from store
    conversation = conversation_store.get(conversation_id)
    if not conversation:
        # Handle missing conversation
        client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            text="Unable to process: Conversation data not found.",
            blocks=[]
        )
        return
    
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
    response = claude.send_tool_result(conversation, request_id, tool_result)
    
    # Update conversation store with latest conversation
    conversation_store[conversation_id] = response.conversation
    
    # Handle Claude's response to the tool result
    event = {"channel": body["channel"]["id"], "ts": body["message"]["thread_ts"]}
    handle_claude_response(client, event, say, claude, response)

def handle_tool_denial(client, body, say):
    """Handle user denial of tool use"""
    # Parse payload value for conversation_id and request_id
    payload = json.loads(body["actions"][0]["value"])
    conversation_id = payload["conversation_id"]
    request_id = payload["request_id"]
    
    # Retrieve conversation from store
    conversation = conversation_store.get(conversation_id)
    if not conversation:
        # Handle missing conversation
        client.chat_update(
            channel=body["channel"]["id"],
            ts=body["message"]["ts"],
            text="Unable to process: Conversation data not found.",
            blocks=[]
        )
        return
    
    # Update message to show denial
    client.chat_update(
        channel=body["channel"]["id"],
        ts=body["message"]["ts"],
        text="Tool use denied.",
        blocks=[]
    )
    
    # Inform Claude that tool use was denied
    claude = ClaudeClient()
    response = claude.notify_tool_denial(conversation, request_id)
    
    # Update conversation store with latest conversation
    conversation_store[conversation_id] = response.conversation
    
    # Handle Claude's response to the denial
    event = {"channel": body["channel"]["id"], "ts": body["message"]["thread_ts"]}
    handle_claude_response(client, event, say, claude, response)

def post_message(say, content, event):
    """Post message to Slack channel or thread"""
    if "thread_ts" in event:
        say(text=content, thread_ts=event["thread_ts"])
    else:
        say(text=content)
