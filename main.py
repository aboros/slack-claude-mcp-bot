import os
from slack_bolt import App
from mcp_manager import MCPManager

# Load environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

# Import handlers
from slack_client import handle_mention, handle_tool_approval, handle_tool_denial, mcp_manager

def main():
    # Initialize MCP servers from config
    global mcp_manager
    mcp_manager = MCPManager("mcp.config.json")
    
    # Initialize slack bolt app
    app = App(token=SLACK_BOT_TOKEN)
    
    # Register event handlers
    app.event("app_mention", handle_mention)
    app.action("approve_tool_use", handle_tool_approval)
    app.action("deny_tool_use", handle_tool_denial)
    
    # Start the app
    app.start(port=3000)

if __name__ == "__main__":
    main()
