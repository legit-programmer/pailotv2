from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client



class MCPManager:
    def __init__(self):
        self.mcp_instances: dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.all_tools = []

    async def register_http_mcp(self, mcp_name, url):
        print(f"Registering HTTP MCP {mcp_name} with URL: {url}")
        read, write, session_id = await self.exit_stack.enter_async_context(
            streamable_http_client(url)
        )
        self.mcp_instances[mcp_name] = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.mcp_instances[mcp_name].initialize()
        print(f"Registered HTTP mcp {mcp_name} with session ID: {session_id}")

    async def register_local_mcp(self, mcp_name, command: list[str]):
        print(f"Registering local MCP {mcp_name} with command: {command}")
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

        print(f"Registered local mcp {mcp_name}")

    def get_mcp(self, mcp_name):
        return self.mcp_instances.get(mcp_name)

    def unregister_mcp(self, mcp_name):
        if mcp_name in self.mcp_instances:
            del self.mcp_instances[mcp_name]

    async def discover_all_tools(self):
        print("Discovering tools from all registered MCPs...")
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
            print(f"No MCP found for tool {tool['name']} with mcp_of {mcp_name}")
            return None
        print(f"Calling tool {tool['name']} from MCP {mcp_name} with args {args}")
        result = await mcp.call_tool(tool["name"], args)
        return result