from agent.session_manager import SessionManager
from mcps.mcp_manager import MCPManager
from models.response import Response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
from config import get_config
from agent.prompts import SYSTEM_PROMPT
from agent.tools import configure_all_tools, call_tools, execute_command, read_file, write_file
from models.model_tools import Tool, get_model_tools, ModelTools
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI


config = get_config()

class Agent:
    def __init__(self, tools: ModelTools, model_name, mcp_manager: MCPManager = None, session_manager: SessionManager=None):
        self.tools = tools
        self.tool_map = {
            "execute_command": execute_command,
            "write_file": write_file,
            "read_file": read_file
        }
        self.model_name = model_name
        self.llm = None
        self.response_parser = None
        self.mcp_tools = None
        self.mcp_manager = mcp_manager
        self.session_manager = session_manager
    
    async def initialize(self):
        if self.mcp_manager:
            self.mcp_tools = await self.mcp_manager.discover_all_tools()
            print(f"MCP tools discovered: {[t['name'] for t in self.mcp_tools]}")
        all_tools = self.tools.model_dump_json() + "\n" + str(self.mcp_tools) if self.mcp_tools else ""
        system_prompt = SYSTEM_PROMPT.format(tools=all_tools, operating_system="Windows")
        self.session_manager.set_base_prompt(SystemMessage(content=system_prompt))

    async def initialize_openai(self):
        await self.initialize()
        self.llm  = ChatOpenAI(model=self.model_name)
        self.response_parser = JsonOutputParser(pydantic_object=Response)

    async def initialize_google_genai(self):
        await self.initialize()
        self.llm = ChatGoogleGenerativeAI(model=self.model_name)
        self.response_parser = JsonOutputParser(pydantic_object=Response)

    async def inference(self, message: str, session_id: str = "default_session") -> Response:
        session = self.session_manager.get_session(session_id)
        if not session:
            self.session_manager.create_session(session_id)
            session = self.session_manager.get_session(session_id)
        messages = session["messages"]
        messages.append(HumanMessage(message))
        response = await self.llm.ainvoke(messages)
        response = response.content
        messages.append(AIMessage(content=response))
        try:
            parsed_response = self.response_parser.parse(response)
        except Exception as e:
            print("Error parsing response:", e)
            parsed_response = {}
        return Response(**parsed_response)
    
    

async def main():
    configure_all_tools()
    mcp_manager = MCPManager()
    session_manager = SessionManager()
    await mcp_manager.register_local_mcp("playwright", ["npx", "@playwright/mcp@latest", "--browser", "chromium", "--headless"])
    await mcp_manager.register_http_mcp("tavily_web_search", "https://mcp.tavily.com/mcp/?tavilyApiKey=" + config.tavily_api_key)
    await mcp_manager.register_local_mcp("serena", ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"])

    agent = Agent(get_model_tools(), 'gemini-2.5-flash', mcp_manager=mcp_manager, session_manager=session_manager)
    await agent.initialize_google_genai()
    while True:
        user_msg = input(">")
        response  = await agent.inference(user_msg)
        while response.tool_call:
        
            result = await call_tools(response.tool_calls, agent)   
            
            try:
                response = await agent.inference(f"The result of the tool calls is: {result}")
            except Exception as e:
                print(f"Error during inference: {e}")
                input("Press Enter to continue...")

        print(response.response)


asyncio.run(main())