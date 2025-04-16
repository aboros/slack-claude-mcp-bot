import pytest
from unittest.mock import MagicMock, patch
import main
from main import mcp_manager

class TestMain:
    """Test suite for the main module"""

    @patch('main.App')
    @patch('main.MCPManager')
    def test_main_initialization(self, mock_mcp_manager_class, mock_app_class):
        """Test initialization of the main app"""
        # Setup
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance
        
        mock_mcp_instance = MagicMock()
        mock_mcp_manager_class.return_value = mock_mcp_instance
        
        # Execute
        with patch.object(main, 'mcp_manager', mock_mcp_instance):
            # Reset imported handlers to use our mocked mcp_manager
            with patch('main.handle_mention'), \
                 patch('main.handle_tool_approval'), \
                 patch('main.handle_tool_denial'):
                main.main()
        
        # Verify
        mock_mcp_manager_class.assert_called_with("mcp.config.json")
        mock_app_class.assert_called_once()
        
        # Check event handlers are registered
        assert mock_app_instance.event.called
        assert mock_app_instance.action.called
        assert mock_app_instance.start.called

    @patch('slack_bolt.App')
    def test_slack_event_registration(self, mock_app_class):
        """Test that Slack event handlers are properly registered"""
        # Setup
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance
        
        mock_event = MagicMock()
        mock_app_instance.event.return_value = mock_event
        
        mock_action = MagicMock()
        mock_app_instance.action.return_value = mock_action
        
        # Execute
        with patch('main.handle_mention') as mock_handle_mention, \
             patch('main.handle_tool_approval') as mock_handle_approval, \
             patch('main.handle_tool_denial') as mock_handle_denial, \
             patch.object(main, 'mcp_manager', MagicMock()):
            main.main()
        
        # Verify
        mock_app_instance.event.assert_called_with("app_mention")
        mock_event.assert_called_once()
        
        mock_app_instance.action.assert_any_call("approve_tool")
        mock_app_instance.action.assert_any_call("deny_tool")
        assert mock_action.call_count == 2

    @patch('os.environ')
    def test_environment_variable_handling(self, mock_environ):
        """Test handling of environment variables"""
        # Setup
        mock_environ.get.side_effect = lambda key, default=None: {
            "SLACK_BOT_TOKEN": "xoxb-test-token-123",
            "SLACK_SIGNING_SECRET": "test-signing-secret",
            "CLAUDE_API_KEY": "test-claude-api-key"
        }.get(key, default)
        
        # Import-time environment variable access
        with patch('main.MCPManager'), \
             patch('main.App'), \
             patch('main.handle_mention'), \
             patch('main.handle_tool_approval'), \
             patch('main.handle_tool_denial'):
            # Re-import to trigger environment variable access
            import importlib
            importlib.reload(main)
        
        # Verify environment variables were accessed
        mock_environ.get.assert_any_call("SLACK_BOT_TOKEN")
        mock_environ.get.assert_any_call("CLAUDE_API_KEY")

    @patch('main.MCPManager')
    def test_mcp_manager_initialization(self, mock_mcp_manager_class):
        """Test that MCPManager is initialized correctly"""
        # Setup
        mock_mcp_instance = MagicMock()
        mock_mcp_manager_class.return_value = mock_mcp_instance
        
        # Execute - reload the module to trigger initialization
        with patch.dict('sys.modules', {'main': None}):
            import importlib
            importlib.reload(main)
        
        # Verify
        mock_mcp_manager_class.assert_called_with("mcp.config.json") 