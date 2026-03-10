from contextlib import AsyncExitStack
import json
import logging
from logging import config

logger = logging.getLogger(__name__)
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from gateway.utils import resolve_env_variable



class MCPManager:
    def __init__(self, config_path="config.json"):
        self.mcp_instances: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.all_tools = []
        self.config_path = config_path

    async def configure_from_file(self):
        try:
            with open(self.config_path, "r") as f:
                mcp_config = json.load(f)
            
            for mcp in mcp_config.get("mcps", []):
                name = mcp.get("name")
                mcp_type = mcp.get("type")
                if mcp_type == "local":
                    command = mcp.get("command")
                    if command:
                        command = resolve_env_variable(command)
                        await self.register_local_mcp(name, command)
                elif mcp_type == "http":
                    url = mcp.get("url")
                    if url:
                        url = resolve_env_variable(url)
                        await self.register_http_mcp(name, url)
        except Exception as e:
            logger.error(f"Failed to load or parse config.json for MCP configuration: {e}")

    async def register_http_mcp(self, mcp_name, url):
        logger.info(f"Registering HTTP MCP {mcp_name} with URL: {url}")
        read, write, session_id = await self.exit_stack.enter_async_context(
            streamable_http_client(url)
        )
        self.mcp_instances[mcp_name] = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.mcp_instances[mcp_name].initialize()
        logger.info(f"Registered HTTP mcp {mcp_name} with session ID: {session_id}")

    async def register_local_mcp(self, mcp_name, command: list[str]):
        logger.info(f"Registering local MCP {mcp_name} with command: {command}")
        server_params = StdioServerParameters(
            command=command[0],
            args=command[1:],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        self.mcp_instances[mcp_name] = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self.mcp_instances[mcp_name].initialize()

        logger.info(f"Registered local mcp {mcp_name}")

    def get_mcp(self, mcp_name):
        return self.mcp_instances.get(mcp_name)

    def unregister_mcp(self, mcp_name):
        if mcp_name in self.mcp_instances:
            del self.mcp_instances[mcp_name]

    async def discover_all_tools(self):
        logger.info("Discovering tools from all registered MCPs...")
        self.all_tools = []
        for mcp_name, mcp in self.mcp_instances.items():
            if isinstance(mcp, ClientSession):
                tools_response = await mcp.list_tools()
                tools = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.inputSchema,
                        "mcp_of": mcp_name
                    }
                    for t in tools_response.tools
                ]
                self.all_tools.extend(tools)
        return self.all_tools
    
    async def get_all_tools(self):
        if not self.all_tools:
            await self.discover_all_tools()
        return self.all_tools
    
    async def call_tool(self, tool_name: str, args):
        all_tools = await self.get_all_tools()
        tool = next((t for t in all_tools if t["name"] == tool_name), None)
        if not tool:
            return None
        mcp_name = tool.get("mcp_of")
        mcp = self.get_mcp(mcp_name)
        if not mcp:
            logger.error(f"No MCP found for tool {tool['name']} with mcp_of {mcp_name}")
            return None
        logger.info(f"Calling tool {tool['name']} from MCP {mcp_name} with args {args}")
        result = await mcp.call_tool(tool["name"], args)
        return result