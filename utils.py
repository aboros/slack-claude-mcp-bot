import logging
import json
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        raise

def format_tool_parameters(params: Dict[str, Any]) -> str:
    """Format tool parameters for display in Slack message"""
    return json.dumps(params, indent=2)

def parse_slack_message(message: str, bot_user_id: Optional[str] = None) -> str:
    """
    Parse a Slack message to extract the relevant text
    Removes bot mentions and any Slack-specific formatting
    """
    # Remove bot mention if present
    if bot_user_id and f"<@{bot_user_id}>" in message:
        message = message.replace(f"<@{bot_user_id}>", "").strip()
    
    # Remove other Slack formatting as needed
    # This could be expanded based on specific needs
    
    return message

def format_message_for_claude(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Format Slack messages for Claude API format"""
    formatted = []
    for msg in messages:
        # Skip bot messages if needed
        if msg.get("bot_id"):
            continue
        
        # Determine role based on message properties
        role = "human" if not msg.get("bot_id") else "assistant"
        
        # Extract and clean text
        text = msg.get("text", "")
        
        formatted.append({
            "role": role,
            "content": text
        })
    
    return formatted

def validate_mcp_config(config: Dict[str, Any]) -> bool:
    """Validate MCP configuration"""
    # Check if servers section exists
    if "servers" not in config:
        logger.error("Missing 'servers' section in MCP config")
        return False
    
    # Check each server configuration
    for i, server in enumerate(config["servers"]):
        if "name" not in server:
            logger.error(f"Server #{i+1} is missing 'name' field")
            return False
            
        if "command" not in server and "module" not in server:
            logger.error(f"Server '{server.get('name', f'#{i+1}')}' needs either 'command' or 'module' field")
            return False
    
    return True
