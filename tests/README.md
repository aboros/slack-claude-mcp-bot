# Slack Bot Test Suite

This directory contains the test suite for the Slack Bot application. The tests are implemented following the test strategy outlined in `documents/test_strategy.md`.

## Test Structure

- **Unit Tests**: Tests for individual components in isolation
  - `test_mcp_manager.py`: Tests for the MCP server manager
  - `test_claude_client.py`: Tests for the Claude API client
  - `test_slack_handlers.py`: Tests for the Slack event and action handlers
  - `test_utils.py`: Tests for utility functions

- **Integration Tests**: Tests for interactions between components
  - `test_integration.py`: Tests for the full flow between Slack, Claude and MCP

- **Main Module Tests**: Tests for application setup
  - `test_main.py`: Tests for the main module initialization

## Test Fixtures

- `conftest.py`: Common fixtures for all test modules
- `test_mcp.config.json`: Test configuration for MCP servers and tools
- `mock_slack_payloads.py`: Various Slack event payloads for testing different structures

## Running Tests

To run all tests:
```bash
pytest
```

To run a specific test file:
```bash
pytest tests/test_mcp_manager.py
```

To run a specific test:
```bash
pytest tests/test_mcp_manager.py::TestMCPManager::test_initialization
```

To run with coverage:
```bash
pytest --cov=. --cov-report=term-missing
```

## Test Configuration

Test configuration is stored in `pytest.ini` with the following settings:
- Verbose output
- Coverage reporting
- Custom markers for unit, integration, and end-to-end tests

## Test Environment

Tests use mocked external dependencies to avoid requiring actual services:
- Anthropic API: Mocked responses for Claude interactions
- Slack API: Mocked responses for Slack interactions
- MCP Servers: Mocked server processes and tools

## Adding New Tests

When adding new features to the application:
1. Create or update the appropriate test file following the existing patterns
2. Add unit tests for any new functions or classes
3. Update integration tests if component interactions change
4. Ensure all tests pass before merging changes 

## Testing Slack Event Handling

The SlackClient handler tests include specific test cases for:

- Thread timestamp extraction from different event structures
- Fallback mechanisms for retrieving thread timestamps
- Handling of interactive components with various payload structures
- Message threading in different contexts (direct messages, channels, threads)

When updating Slack handlers, ensure tests cover all possible event payload structures, as these can vary depending on:
- Event type (message, interaction, etc.)
- Context (channel message, thread reply, direct message)
- Interaction type (button click, modal submission, etc.)

## Regression Testing

When fixing bugs, especially those related to Slack event handling:
1. Create a new test case that reproduces the issue
2. Verify the fix resolves the issue
3. Ensure the test is added to the appropriate test suite
4. Document the issue and solution in code comments 