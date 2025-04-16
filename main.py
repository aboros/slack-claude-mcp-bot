import logging
import os
from slack_bolt import App
from mcp_manager import MCPManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")

# Initialize MCP servers from config globally
mcp_manager = MCPManager("mcp.config.json")

# Import handlers after defining mcp_manager to avoid circular imports
from slack_client import handle_mention, handle_tool_approval, handle_tool_denial

def main():
    # Initialize slack bolt app
    app = App(
        token=SLACK_BOT_TOKEN,
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )
    
    # Register event handlers
    app.event("app_mention")(handle_mention)
    app.action("approve_tool")(handle_tool_approval)
    app.action("deny_tool")(handle_tool_denial)
    
    # Start the app
    app.start(port=3000)

if __name__ == "__main__":
    main()
