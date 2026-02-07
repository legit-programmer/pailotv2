from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
from dotenv import load_dotenv
from agent.prompts import SYSTEM_PROMPT
from agent.tools import configure_all_tools
from models.model_tools import get_model_tools, ModelTools

load_dotenv()

class Agent:
    def __init__(self, tools: ModelTools, model_name):
        self.messages = []
        self.tools = tools
        self.model_name = model_name
        self.llm = None
        self.initialize()
    
    def initialize(self):
        print(self.tools.model_dump_json())

    def initialize_openai(self):
        self.llm  = ChatOpenAI(model=self.model_name)

    async def inference(self, message: str):
        self.messages.append(HumanMessage(message))
        response = await self.llm.ainvoke(self.messages)
        response = response.content
        self.messages.append(AIMessage(response))
        return response
    


async def main():
    configure_all_tools()
    agent = Agent(get_model_tools(), 'gpt-4o')
    agent.initialize_openai()
    while True:
        user_msg = input(">")
        print(await agent.inference(user_msg))


asyncio.run(main())