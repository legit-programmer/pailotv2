from typing import Literal

from agent.session_manager import SessionManager
from mcps.mcp_manager import MCPManager
from models.response import Response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
import json
import logging
from config import get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from agent.prompts import SYSTEM_PROMPT
from agent.tools import configure_all_tools, call_tools, execute_command, read_file, write_file
from models.model_tools import Tool, get_model_tools, ModelTools
from langchain_core.output_parsers import JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from datetime import datetime
from gateway.utils import evaluate_provider

from models.session import CreateSessionRequest
from agent.tool_registry import get_tool_registry

config = get_config()



class Agent:
    def __init__(self, tools: ModelTools, model_name, mcp_manager: MCPManager = None, session_manager: SessionManager = None, filter_tools_by_name: list = None, filter_tools_by_mcp_of: list = None):
        self.tools = tools
        self.tool_map = {tool.name: tool.function for tool in tools.tools}
        self.model_name = model_name
        self.llm = None
        self.response_parser = None
        self.mcp_tools = None
        self.mcp_manager = mcp_manager
        self.session_manager = session_manager
        self.tool_registry = None
        self.filter_tools_by_name = filter_tools_by_name
        self.filter_tools_by_mcp_of = filter_tools_by_mcp_of

    async def initialize(self):
        if self.mcp_manager:
            await self.mcp_manager.configure_from_file()
            if not self.filter_tools_by_name and not self.filter_tools_by_mcp_of:
                self.mcp_tools = await self.mcp_manager.discover_all_tools()
                logger.info(f"No tool filtering applied. All discovered MCP tools are added to context.")
            else:
                logger.info(f"Applying tool filtering. filter_tools_by_name: {self.filter_tools_by_name}, filter_tools_by_mcp_of: {self.filter_tools_by_mcp_of}")
                self.mcp_tools = await self.mcp_manager.get_filtered_tools(filter=self.filter_tools_by_name if self.filter_tools_by_name else self.filter_tools_by_mcp_of, by_name=True if self.filter_tools_by_name else False)


            logger.info(f"MCP tools discovered: {[t['name'] for t in self.mcp_tools]}")
        all_tools = self.tools.model_dump_json() + "\n" + \
            str(self.mcp_tools) if self.mcp_tools else ""
        self.tool_registry = get_tool_registry()
        system_prompt = SYSTEM_PROMPT.format(
            tools=all_tools, operating_system=config.operating_system, current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
            self.session_manager.create_session(CreateSessionRequest(session_id=session_id, model=self.llm.model))
            session = self.session_manager.get_session(session_id)
        
        if not self.llm.model.startswith(session.model):
            try:
                self.llm = evaluate_provider(session.model)
            except Exception as e:
                raise ValueError(f"Model provider for {session.model} not found: {e}")
            
        messages = session.messages
        messages.append(HumanMessage(message))
        
        # Dynamically inject the most up-to-date system prompt at the very beginning
        inference_messages = [self.session_manager.base_prompt] + messages if self.session_manager.base_prompt else messages
        
        logger.info(f"inferencing {self.llm.model} now..")
        response = await self.llm.ainvoke(inference_messages)
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
            logger.error(f"Error parsing response: {e}")
            parsed_response = {}
        return Response(**parsed_response)

agent = None

async def configure_global_agent(provider: Literal["openai", "google_genai", "ollama"] = "google_genai", model_name: str = "gemini-3.1-flash-lite-preview") -> Agent:
    global agent
    configure_all_tools() 
    mcp_manager = MCPManager()
    session_manager = SessionManager()

    agent = Agent(get_model_tools(), model_name,
                  mcp_manager=mcp_manager, session_manager=session_manager, filter_tools_by_mcp_of=["serena"])
    await agent.initialize_model(provider=provider, model_name=model_name)
    return agent



async def get_global_agent() -> Agent:
    global agent
    if agent is None:
        raise ValueError("Global agent is not initialized yet. Please call configure_global_agent() first.")
    return agent


async def loop(user_msg, session_id):
    global agent
    if agent is None:
        raise ValueError("Global Agent is not initialized yet. Please call configure_global_agent() first.")

    while True:
        response = await agent.inference(user_msg, session_id=session_id)
        while response.tool_call:

            steering_messages = agent.session_manager.get_steering_messages(session_id)
            if steering_messages:
                response = await agent.inference(f"""User interrupted, added messages: {",".join(steering_messages)}""", session_id=session_id)
                continue
            

            result = await call_tools(response.tool_calls, agent)
            logger.info("pushing results to context")
            prompt = f" Here are the results of the tool calls: {result}"

            
            steering_messages = agent.session_manager.get_steering_messages(session_id)
            if steering_messages:
                prompt = f"{prompt}\nHowever, the user has also added some additional messages while the tools were being called.\nAdded messages: {",".join(steering_messages)}"
            
            
            try:
                response = await agent.inference(prompt, session_id=session_id)
            except Exception as e:
                logger.error(f"Error during inference: {e}")
                return f"Error during inference: {e}"

        agent.session_manager.save_session(agent.session_manager.get_session(session_id))
        return response.response
