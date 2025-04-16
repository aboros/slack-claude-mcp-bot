import json
import logging
import subprocess
import time
import psutil
import os
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if we're running in test mode
TESTING = os.environ.get("TESTING", "0") == "1"

class MCPManager:
    """Manager for MCP servers and client functionality combined"""
    
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
        if not TESTING:
            self.start_mcp_servers()
        else:
            logger.info("Running in test mode, skipping MCP server startup")
        
        # Initialize MCP client SDK
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Initialize MCP client SDK connection"""
        try:
            # Import MCP SDK
            if not TESTING:
                from mcp.client.stdio import stdio_client, StdioServerParameters
                # Initialize with the first server config or a default
                server_config = self.config.get("servers", [{}])[0]
                server_name = server_config.get("name", "default-server")
                server_cmd = server_config.get("command", "")
                server_args = server_config.get("args", [])
                
                # Create server parameters for the stdio client
                server_params = StdioServerParameters(
                    command=server_cmd if server_cmd else "echo", 
                    args=server_args
                )
                
                # Create the client
                client = stdio_client(server=server_params)
                logger.info("MCP Client initialized successfully")
                return client
            else:
                # Use a mock client for testing
                from tests.mock_mcp import Client
                client = Client()
                logger.info("Mock MCP Client initialized for testing")
                return client
        except ImportError:
            logger.error("Failed to import MCP SDK. Make sure it's installed.")
            raise
    
    def start_mcp_servers(self):
        """Start all configured MCP servers"""
        try:
            # Import MCP SDK
            if not TESTING:
                from mcp.server import Server
            else:
                from tests.mock_mcp import start_server
            
            # Start each server based on config
            for server_config in self.config.get("servers", []):
                server_name = server_config.get("name", "unnamed-server")
                server_cmd = server_config.get("command")
                server_args = server_config.get("args", [])
                
                if server_cmd:
                    # Start server as subprocess
                    logger.info(f"Starting MCP server '{server_name}'")
                    process = self._start_process(server_cmd, server_args)
                    self.server_processes[server_name] = process
                    
                    # Check if process is still running
                    if not self._is_process_running(process):
                        logger.error(f"Server '{server_name}' failed to start")
                    else:
                        logger.info(f"Server '{server_name}' started successfully (PID: {process.pid})")
                else:
                    # Use SDK to start server
                    logger.info(f"Starting MCP server '{server_name}' via SDK")
                    if not TESTING:
                        # Create an MCP server instance
                        version = server_config.get("version", "1.0.0")
                        instructions = server_config.get("instructions", "")
                        
                        # This is just creating the server object, would need to be run separately
                        # in an async context with proper streams for actual server operation
                        server = Server(name=server_name, version=version, instructions=instructions)
                        
                        # Note: To actually run the server, you would need to call server.run()
                        # with appropriate streams in an async context
                        logger.warning(f"Server '{server_name}' object created but not running - " 
                                       f"use a dedicated script with async context to run MCP servers")
                    else:
                        start_server(server_config)
        except ImportError:
            logger.error("Failed to import MCP SDK. Make sure it's installed.")
            raise
        except Exception as e:
            logger.error(f"Error starting MCP servers: {e}")
            raise
    
    def _start_process(self, cmd: str, args: List[str]) -> psutil.Process:
        """Start a process using psutil for better management"""
        process = subprocess.Popen(
            [cmd] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return psutil.Process(process.pid)
    
    def _is_process_running(self, process: psutil.Process) -> bool:
        """Check if a process is running using psutil"""
        try:
            # Give the process a moment to start
            time.sleep(0.5)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools from MCP servers"""
        try:
            tools = self.client.list_tools()
            logger.info(f"Retrieved {len(tools)} tools from MCP servers")
            return tools
        except Exception as e:
            logger.error(f"Error retrieving tools: {e}")
            return []
    
    def execute_tool(self, request_id: str) -> Dict[str, Any]:
        """Execute tool via MCP"""
        try:
            result = self.client.execute_tool(request_id)
            logger.info(f"Tool execution for request {request_id} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Error executing tool for request {request_id}: {e}")
            return {"error": str(e)}
    
    def restart_server(self, server_name: str) -> bool:
        """Restart a specific MCP server"""
        if server_name not in self.server_processes:
            logger.error(f"Cannot restart unknown server '{server_name}'")
            return False
        
        logger.info(f"Restarting MCP server '{server_name}'")
        process = self.server_processes[server_name]
        
        # Gracefully terminate the process
        try:
            process.terminate()
            gone, alive = psutil.wait_procs([process], timeout=5)
            if process in alive:
                logger.warning(f"Server '{server_name}' did not terminate gracefully, killing...")
                process.kill()
        except psutil.NoSuchProcess:
            logger.warning(f"Server '{server_name}' already stopped")
        
        # Get the original command and args
        server_config = next((s for s in self.config.get("servers", []) 
                              if s.get("name") == server_name), None)
        if not server_config:
            logger.error(f"Cannot find configuration for server '{server_name}'")
            return False
        
        server_cmd = server_config.get("command")
        server_args = server_config.get("args", [])
        
        # Restart the process
        new_process = self._start_process(server_cmd, server_args)
        self.server_processes[server_name] = new_process
        
        if self._is_process_running(new_process):
            logger.info(f"Server '{server_name}' restarted successfully (PID: {new_process.pid})")
            return True
        else:
            logger.error(f"Failed to restart server '{server_name}'")
            return False
    
    def get_server_status(self, server_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get status of all servers or a specific server"""
        status = {}
        
        servers = [server_name] if server_name else self.server_processes.keys()
        
        for name in servers:
            if name not in self.server_processes:
                status[name] = {"status": "unknown", "error": "Server not found"}
                continue
            
            process = self.server_processes[name]
            try:
                proc_status = process.status()
                cpu_percent = process.cpu_percent(interval=0.1)
                memory_info = process.memory_info()
                
                status[name] = {
                    "pid": process.pid,
                    "status": proc_status,
                    "running": process.is_running(),
                    "cpu_percent": cpu_percent,
                    "memory_rss": memory_info.rss,
                    "memory_vms": memory_info.vms,
                    "create_time": process.create_time()
                }
            except psutil.NoSuchProcess:
                status[name] = {"status": "stopped", "running": False, "error": "Process not found"}
        
        return status
    
    def stop_server(self, server_name: str) -> bool:
        """Stop a specific MCP server"""
        if server_name not in self.server_processes:
            logger.error(f"Cannot stop unknown server '{server_name}'")
            return False
        
        logger.info(f"Stopping MCP server '{server_name}'")
        process = self.server_processes[server_name]
        
        try:
            process.terminate()
            gone, alive = psutil.wait_procs([process], timeout=5)
            if process in alive:
                logger.warning(f"Server '{server_name}' did not terminate gracefully, killing...")
                process.kill()
                gone, alive = psutil.wait_procs([process], timeout=3)
                if process in alive:
                    logger.error(f"Could not kill server '{server_name}'")
                    return False
            
            del self.server_processes[server_name]
            return True
        except psutil.NoSuchProcess:
            logger.warning(f"Server '{server_name}' already stopped")
            del self.server_processes[server_name]
            return True
    
    def __del__(self):
        """Clean up server processes on shutdown"""
        for name, process in list(self.server_processes.items()):
            try:
                if process.is_running():
                    logger.info(f"Terminating MCP server '{name}' (PID: {process.pid})")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except psutil.TimeoutExpired:
                        logger.warning(f"Server '{name}' didn't terminate gracefully, forcing...")
                        process.kill()
            except psutil.NoSuchProcess:
                pass  # Process already gone
