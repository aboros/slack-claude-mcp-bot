import json
import logging
import subprocess
import time
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self):
        try:
            # Import MCP SDK
            from mcp import Client
            self.client = Client()
            logger.info("MCP Client initialized successfully")
        except ImportError:
            logger.error("Failed to import MCP SDK. Make sure it's installed.")
            raise
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP servers"""
        try:
            # This is a placeholder - actual implementation depends on MCP SDK
            tools = self.client.list_tools()
            logger.info(f"Retrieved {len(tools)} tools from MCP servers")
            return tools
        except Exception as e:
            logger.error(f"Error retrieving tools: {e}")
            return []
    
    def execute_tool(self, request_id: str) -> Dict[str, Any]:
        """Execute tool via MCP"""
        try:
            # This is a placeholder - actual implementation depends on MCP SDK
            result = self.client.execute_tool(request_id)
            logger.info(f"Tool execution for request {request_id} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool for request {request_id}: {e}")
            return {"error": str(e)}


class MCPManager:
    """Manager for MCP servers"""
    
    def __init__(self, config_path: str):
        """Initialize MCP servers from config"""
        self.config_path = config_path
        self.server_processes = {}
        
        # Load configuration
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
            logger.info(f"Loaded MCP configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading MCP configuration: {e}")
            raise
        
        # Start MCP servers
        self.start_mcp_servers()
        
        # Initialize MCP client
        self.client = MCPClient()
    
    def start_mcp_servers(self):
        """Start all configured MCP servers"""
        try:
            # Import MCP SDK
            from mcp import start_server
            
            # Start each server based on config
            for server_config in self.config.get("servers", []):
                server_name = server_config.get("name", "unnamed-server")
                server_cmd = server_config.get("command")
                server_args = server_config.get("args", [])
                
                if server_cmd:
                    # Start server as subprocess
                    logger.info(f"Starting MCP server '{server_name}'")
                    process = subprocess.Popen(
                        [server_cmd] + server_args,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    self.server_processes[server_name] = process
                    
                    # Give the server a moment to start
                    time.sleep(1)
                    
                    # Check if process is still running
                    if process.poll() is not None:
                        stdout, stderr = process.communicate()
                        logger.error(f"Server '{server_name}' failed to start: {stderr.decode()}")
                    else:
                        logger.info(f"Server '{server_name}' started successfully (PID: {process.pid})")
                else:
                    # Use SDK to start server
                    logger.info(f"Starting MCP server '{server_name}' via SDK")
                    # This is a placeholder - actual implementation depends on MCP SDK
                    start_server(server_config)
        except ImportError:
            logger.error("Failed to import MCP SDK. Make sure it's installed.")
            raise
        except Exception as e:
            logger.error(f"Error starting MCP servers: {e}")
            raise
    
    def get_available_tools(self):
        """Get list of available tools from MCP servers"""
        return self.client.list_tools()
    
    def execute_tool(self, request_id):
        """Execute tool via MCP"""
        return self.client.execute_tool(request_id)
    
    def __del__(self):
        """Clean up server processes on shutdown"""
        for name, process in self.server_processes.items():
            if process.poll() is None:  # If process is still running
                logger.info(f"Terminating MCP server '{name}' (PID: {process.pid})")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Server '{name}' didn't terminate gracefully, forcing...")
                    process.kill()
