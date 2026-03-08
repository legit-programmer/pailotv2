# pailotv2 — Overview

My implementation of OpenClaw but in Python. Occupies around 800 MB of memory when running, including the playwright (browser) and Serena (shell executor) mcp. Currently only supports a discord bot interface, but the architecture is designed to be modular and support multiple interfaces (like Telegram, Slack, etc.) in the future.

## Tools and mcps

Pailot uses a modular tool system, where tools can be registered with the MCP manager and then used by the agent. Currently, there are two MCPs: a playwright MCP for web automation and a Serena MCP for shell command execution. The tools are defined locally in `agent/agent.py` and registered with the MCP manager when the agent is initialized. You can add or remove mcp servers as its modular and they will be automatically picked up by the agent.

```python
await mcp_manager.register_local_mcp("playwright", ["npx", "@playwright/mcp@latest", "--browser", "chromium"])
await mcp_manager.register_http_mcp("tavily_web_search", "https://mcp.tavily.com/mcp/?tavilyApiKey=" + config.tavily_api_key)
await mcp_manager.register_local_mcp("serena", ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"])
```

## Screenshots

Here is pailot configuring a startup service for itself on a vps machine.

![alt text](assets/image-1.png)

## Running locally
1. Get a discord bot token and invite the bot to your server.
2. Create a `.env` file in the root of the project and add the following variables:
  ```
  DISCORD_MASTER_USER_ID=your_discord_user_id
  BOT_TOKEN=your_discord_bot_token
  GEMINI_API_KEY=your_gemini_api_key # use OPENAI_API_KEY if you want, but the agent runs on gemini by default, make sure you run >change_model <model_name> command in the discord server to switch to the model you want to use.
  OS=windows/linux/mac
  TAVILY_API_KEY=your_tavily_api_key (optional, only needed if you want to use the web search tool, unregister from agent/agent.py if you don't want to use it)
  ```
3. Install the dependencies:
```
pip install -r requirements.txt
```
4. Run the agent:
```
python -m gateway.gateway
```
This spins up the fastapi gateway server along with the discord bot script. The bot will automatically connect to the gateway server and be ready to receive commands.

### Note

This project is under active development and is open for contributions, so if you want to add a new tool or interface, feel free to submit a pull request or open an issue.

