import asyncio
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

class BrowserTool:
    def __init__(self):
        self.session: ClientSession = None
        self.exit_stack = AsyncExitStack()
        self.start_command = [
        "npx", "@playwright/mcp@latest",
        "--browser", "chromium",
        "--headless"
    ]
        
    async def connect(self):
        """Connect to an MCP server via stdio."""
        server_params = StdioServerParameters(
            command=self.start_command[0],
            args=self.start_command[1:],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()


    async def get_tools(self):
        tools_response = await self.session.list_tools()
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
                "mcp_of": "playwright"
            }
            for t in tools_response.tools
        ]
        # print(f"Connected. Tools available: {[t['name'] for t in self.tools]}")
        return tools
    
    async def get_session(self):
        return self.session

    # async def run(self, task: str):
    #     """Agentic loop: keep calling Claude + tools until task is done."""
    #     messages = [{"role": "user", "content": task}]

    #     while True:
    #         response = self.anthropic.messages.create(
    #             model="claude-sonnet-4-5-20250929",
    #             max_tokens=4096,
    #             tools=self.tools,
    #             messages=messages
    #         )

    #         # Append assistant response
    #         messages.append({"role": "assistant", "content": response.content})

    #         # If Claude is done, print final answer
    #         if response.stop_reason == "end_turn":
    #             for block in response.content:
    #                 if hasattr(block, "text"):
    #                     print("\n[Agent]:", block.text)
    #             break

    #         # Handle tool calls
    #         tool_results = []
    #         for block in response.content:
    #             if block.type == "tool_use":
    #                 print(f"\n[Tool Call] {block.name}({block.input})")
    #                 result = await self.session.call_tool(block.name, block.input)
    #                 print(f"[Tool Result] {result.content}")
    #                 tool_results.append({
    #                     "type": "tool_result",
    #                     "tool_use_id": block.id,
    #                     "content": result.content
    #                 })

    #         messages.append({"role": "user", "content": tool_results})

    async def cleanup(self):
        await self.exit_stack.aclose()


# async def main():
#     agent = BrowserTool()

#     # Connect to Playwright MCP server
#     await agent.connect()
#     try:
#         await agent.run("Go to news.ycombinator.com and tell me the top 3 story titles")
#     finally:
#         await agent.cleanup()


# asyncio.run(main())