from typing import Literal

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
from langchain_ollama import ChatOllama
from datetime import datetime

config = get_config()


class Agent:
    def __init__(self, tools: ModelTools, model_name, mcp_manager: MCPManager = None, session_manager: SessionManager = None):
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
            print(
                f"MCP tools discovered: {[t['name'] for t in self.mcp_tools]}")
        all_tools = self.tools.model_dump_json() + "\n" + \
            str(self.mcp_tools) if self.mcp_tools else ""
        system_prompt = SYSTEM_PROMPT.format(
            tools=all_tools, operating_system="Windows", current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.session_manager.set_base_prompt(
            SystemMessage(content=system_prompt))

    async def initialize_model(self, provider: Literal["openai", "google_genai", "ollama"] = "google_genai", model_name: str = "gemini-3.1-flash-lite-preview"):
        await self.initialize()
        if provider == "openai":
            self.llm = ChatOpenAI(model=model_name)
        elif provider == "google_genai":
            self.llm = ChatGoogleGenerativeAI(model=model_name)
        elif provider == "ollama":
            self.llm = ChatOllama(model=model_name)
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
        # Some providers return content as a list of blocks instead of a string
        if isinstance(response, list):
            response = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response
            )
        messages.append(AIMessage(content=response))
        try:
            parsed_response = self.response_parser.parse(response)
            if not isinstance(parsed_response, dict):
                parsed_response = {}
        except Exception as e:
            print("Error parsing response:", e)
            parsed_response = {}
        return Response(**parsed_response)


async def configure_global_agent(provider: Literal["openai", "google_genai", "ollama"] = "google_genai", model_name: str = "gemini-3.1-flash-lite-preview") -> Agent:
    configure_all_tools()
    mcp_manager = MCPManager()
    session_manager = SessionManager()
    await mcp_manager.register_local_mcp("playwright", ["npx", "@playwright/mcp@latest", "--browser", "chromium"])
    await mcp_manager.register_http_mcp("tavily_web_search", "https://mcp.tavily.com/mcp/?tavilyApiKey=" + config.tavily_api_key)
    await mcp_manager.register_local_mcp("serena", ["uvx", "--from", "git+https://github.com/oraios/serena", "serena", "start-mcp-server"])

    agent = Agent(get_model_tools(), model_name,
                  mcp_manager=mcp_manager, session_manager=session_manager)
    await agent.initialize_model(provider=provider, model_name=model_name)
    return agent

agent = None


async def get_global_agent():
    global agent
    if agent is None:
        agent = await configure_global_agent()
    return agent


async def loop(user_msg, session_id):
    global agent
    if agent is None:
        return "Global Agent is not initialized yet. Please try again in a moment."

    while True:
        response = await agent.inference(user_msg, session_id=session_id)
        while response.tool_call:

            result = await call_tools(response.tool_calls, agent)
            print("pushing results to context")
            try:
                print("inferencing now..")
                response = await agent.inference(f"The result of the tool calls is: {result}", session_id=session_id)
            except Exception as e:
                print(f"Error during inference: {e}")
                return f"Error during inference: {e}"

        return response.response
