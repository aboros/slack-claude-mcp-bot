# Slack Bot with Claude Integration and MCP Tools

This application implements a Slack bot that integrates with Claude API and Model Context Protocol (MCP) servers for tool execution.

## Overview

The bot is triggered when a user mentions it in a Slack channel or thread. It processes the message (including thread history if applicable), calls the Claude API, and handles different response types including text, tool use requests, and final answers.

## App Flow

1. **Trigger**: User mentions bot in Slack channel/thread
2. **Message Processing**:
   - Bot captures the mention event
   - If in a thread, bot retrieves the thread history
   - Bot creates a new Claude conversation with available tools

3. **Claude Interaction**:
   - Bot sends the user message to Claude
   - Claude responds with text, tool use request, or final answer
   - For tool use requests, bot asks for user approval

4. **Tool Use Flow**:
   - **If Approved**: Bot executes the tool via MCP and sends result to Claude
   - **If Denied**: Bot informs Claude of the denial

5. **Completion**: Process continues until Claude provides a final answer

## MCP Integration

The application uses the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) SDK to:

- Load tool configurations from `mcp.config.json`
- Launch configured MCP servers at startup
- Provide Claude with a list of available tools
- Execute tool requests as approved by users

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```
   export SLACK_BOT_TOKEN=your_slack_bot_token
   export CLAUDE_API_KEY=your_claude_api_key
   export CLAUDE_MODEL=claude-3-7-sonnet-20250219  # or your preferred model
   ```

3. Customize the `mcp.config.json` file with your desired tool servers

4. Run the application:
   ```
   python main.py
   ```

## Project Structure

- `main.py`: Entry point
- `slack_client.py`: Slack API interactions
- `claude_client.py`: Claude API interactions
- `mcp_manager.py`: MCP server management
- `utils.py`: Helper functions
- `mcp.config.json`: MCP configuration

## Adding Custom Tools

To add custom tools:

1. Create a new MCP server module
2. Add the server configuration to `mcp.config.json`
3. Restart the application
