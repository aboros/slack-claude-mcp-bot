"""
Mock MCP module for testing.
This module provides mock implementations of MCP functionality
to avoid requiring the actual MCP package during tests.
"""

class Client:
    """Mock MCP Client"""
    
    def __init__(self):
        """Initialize the mock client"""
        pass
    
    def list_tools(self):
        """Return a list of mock tools"""
        return [
            {
                "name": "test_tool",
                "description": "A test tool for testing",
                "parameters": {
                    "param1": {"type": "string"},
                    "param2": {"type": "integer"}
                }
            }
        ]
    
    def execute_tool(self, request_id):
        """Execute a mock tool"""
        return {"result": "Tool executed successfully"}


def start_server(config):
    """Mock function to start an MCP server"""
    return True 