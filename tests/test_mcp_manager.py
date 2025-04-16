import pytest
import json
import os
from unittest.mock import MagicMock, patch, mock_open
from mcp_manager import MCPManager

class TestMCPManager:
    """Test suite for the MCPManager class"""

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_initialization(self, mock_start_server, mock_client_class, mock_process_class, mock_popen, mock_config_file):
        """Test MCPManager initialization with valid config"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process
        
        # Set up the config with the expected servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None) as mock_start:
            manager = MCPManager(mock_config_file)
            
            # Manually set server processes as they would be after starting
            manager.server_processes = {
                "test-server-1": mock_process,
                "test-server-2": mock_process
            }
        
        # Verify
        assert manager.config_path == mock_config_file
        assert len(manager.server_processes) == 2
        assert mock_client_class.called
        assert manager.client == mock_client_instance

    @patch('mcp.Client')
    def test_initialization_with_invalid_config(self, mock_client_class, tmp_path):
        """Test MCPManager initialization with invalid config file"""
        # Setup
        invalid_config_path = str(tmp_path / "invalid_config.json")
        with open(invalid_config_path, 'w') as f:
            f.write("This is not valid JSON")
        
        # Execute & Verify
        with pytest.raises(Exception):
            MCPManager(invalid_config_path)

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_get_available_tools(self, mock_start_server, mock_client_class, mock_process_class, 
                               mock_popen, mock_config_file, mock_mcp_client):
        """Test retrieving available tools"""
        # Setup
        mock_client_class.return_value = mock_mcp_client
        
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process
        
        # Set up the manager with mocked start_mcp_servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None):
            manager = MCPManager(mock_config_file)
            # Replace the client with our mock
            manager.client = mock_mcp_client
        
        # Execute
        tools = manager.get_available_tools()
        
        # Verify
        assert tools == mock_mcp_client.list_tools.return_value
        assert mock_mcp_client.list_tools.called

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_execute_tool(self, mock_start_server, mock_client_class, mock_process_class, 
                         mock_popen, mock_config_file, mock_mcp_client):
        """Test executing a tool"""
        # Setup
        mock_client_class.return_value = mock_mcp_client
        
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process
        
        # Set up the manager with mocked start_mcp_servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None):
            manager = MCPManager(mock_config_file)
            # Replace the client with our mock
            manager.client = mock_mcp_client
        
        request_id = "test_request_123"
        
        # Execute
        result = manager.execute_tool(request_id)
        
        # Verify
        assert result == mock_mcp_client.execute_tool.return_value
        mock_mcp_client.execute_tool.assert_called_with(request_id)

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_restart_server(self, mock_start_server, mock_client_class, mock_process_class, 
                           mock_popen, mock_config_file, mock_psutil_process):
        """Test restarting a server"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_process_class.return_value = mock_psutil_process
        
        # Set up the manager with mocked start_mcp_servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None):
            manager = MCPManager(mock_config_file)
            # Manually add a server process to the manager
            server_name = "test-server-1"
            manager.server_processes[server_name] = mock_psutil_process
            # Mock the _start_process method to return our mock process
            manager._start_process = MagicMock(return_value=mock_psutil_process)
        
        # Execute
        result = manager.restart_server(server_name)
        
        # Verify
        assert result is True
        assert mock_psutil_process.terminate.called
        assert manager._start_process.called

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_get_server_status(self, mock_start_server, mock_client_class, mock_process_class, 
                              mock_popen, mock_config_file, mock_psutil_process):
        """Test getting server status"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        # Configure the mock process with required attributes
        mock_process_class.return_value = mock_psutil_process
        mock_psutil_process.memory_info.return_value = MagicMock(rss=1024, vms=2048)
        mock_psutil_process.create_time.return_value = 1609459200  # 2021-01-01
        mock_psutil_process.cpu_percent.return_value = 5.0
        
        # Set up the manager with mocked start_mcp_servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None):
            manager = MCPManager(mock_config_file)
            # Manually add server processes to the manager
            manager.server_processes = {
                "test-server-1": mock_psutil_process,
                "test-server-2": mock_psutil_process
            }
        
        # Execute
        status = manager.get_server_status()
        
        # Verify
        assert len(status) == 2
        assert "test-server-1" in status
        assert status["test-server-1"]["running"] is True
        assert status["test-server-1"]["status"] == "running"
        
    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    @patch('mcp_manager.TESTING', False)  # Override TESTING flag for this test
    def test_stop_server(self, mock_start_server, mock_client_class, mock_process_class, 
                        mock_popen, mock_config_file, mock_psutil_process):
        """Test stopping a server"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_process_class.return_value = mock_psutil_process
        
        # Set up the manager with mocked start_mcp_servers
        with patch.object(MCPManager, 'start_mcp_servers', return_value=None):
            manager = MCPManager(mock_config_file)
            # Manually add a server process to the manager
            server_name = "test-server-1"
            manager.server_processes[server_name] = mock_psutil_process
        
        # Execute
        result = manager.stop_server(server_name)
        
        # Verify
        assert result is True
        assert mock_psutil_process.terminate.called

    @patch('mcp_manager.subprocess.Popen')
    @patch('mcp_manager.psutil.Process')
    @patch('mcp.Client')
    @patch('mcp.start_server')
    def test_stop_nonexistent_server(self, mock_start_server, mock_client_class, mock_process_class, 
                                    mock_popen, mock_config_file):
        """Test stopping a non-existent server"""
        # Setup
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        
        mock_process = MagicMock()
        mock_process.is_running.return_value = True
        mock_process_class.return_value = mock_process
        
        manager = MCPManager(mock_config_file)
        
        # Execute
        result = manager.stop_server("nonexistent-server")
        
        # Verify
        assert result is False 