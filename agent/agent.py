from models.response import Response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
from dotenv import load_dotenv
from agent.prompts import SYSTEM_PROMPT
from agent.tools import configure_all_tools, call_tools
from models.model_tools import get_model_tools, ModelTools
from langchain_core.output_parsers import JsonOutputParser
from mcps.playwright_client import BrowserTool

load_dotenv()

class Agent:
    def __init__(self, tools: ModelTools, model_name, enable_browser=True):
        self.messages = []
        self.tools = tools
        self.model_name = model_name
        self.llm = None
        self.chain = None
        self.response_parser = None
        self.enable_browser = enable_browser
        self.browser_tool = None
        self.mcp_tools = None
    
    async def initialize(self):
        if self.enable_browser:
            self.browser_tool = BrowserTool()
            print("starting playwright mcp server...")
            await self.browser_tool.connect()
            self.mcp_tools = await self.browser_tool.get_tools()
            print(f"Playwright MCP server connected. Tools available: {[t['name'] for t in self.mcp_tools]}")
        all_tools = self.tools.model_dump_json() + "\n" + str(self.mcp_tools) if self.mcp_tools else ""
        system_prompt = SYSTEM_PROMPT.format(tools=all_tools, operating_system="Windows")
        self.messages.append(SystemMessage(system_prompt))

    async def initialize_openai(self):
        await self.initialize()
        self.llm  = ChatOpenAI(model=self.model_name)
        self.response_parser = JsonOutputParser(pydantic_object=Response)


    async def inference(self, message: str):
        self.messages.append(HumanMessage(message))
        response = await self.llm.ainvoke(self.messages)
        response = response.content
        self.messages.append(AIMessage(response))
        try:
            parsed_response = self.response_parser.parse(response)
        except Exception as e:
            print("Error parsing response:", e)
            parsed_response = {}
        return Response(**parsed_response)
    


async def main():
    configure_all_tools()
    agent = Agent(get_model_tools(), 'gpt-5-mini')
    await agent.initialize_openai()
    while True:
        user_msg = input(">")
        response  = await agent.inference(user_msg)
        while response.tool_call:
            result = None
            try:
                
                result = await call_tools(response.tool_calls, available_mcp_tools=agent.mcp_tools, ctx=agent)
            except Exception as e:
                print(f"Error calling tools: {e}")
                result = "Error calling tools"
            
            try:
                response = await agent.inference(f"The result of the tool calls is: {result}")
            except Exception as e:
                print(f"Error during inference: {e}")
                input("Press Enter to continue...")

        print(response.response)


asyncio.run(main())