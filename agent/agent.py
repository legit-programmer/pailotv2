from models.response import Response
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
from dotenv import load_dotenv
from agent.prompts import SYSTEM_PROMPT
from agent.tools import configure_all_tools, call_tools
from models.model_tools import get_model_tools, ModelTools
from langchain_core.output_parsers import JsonOutputParser

load_dotenv()

class Agent:
    def __init__(self, tools: ModelTools, model_name):
        self.messages = []
        self.tools = tools
        self.model_name = model_name
        self.llm = None
        self.chain = None
        self.response_parser = None
        self.initialize()
    
    def initialize(self):
        system_prompt = SYSTEM_PROMPT.format(tools=self.tools.model_dump_json(), operating_system="Windows")
        self.messages.append(SystemMessage(system_prompt))

    def initialize_openai(self):
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
    agent = Agent(get_model_tools(), 'gpt-5.2')
    agent.initialize_openai()
    while True:
        user_msg = input(">")
        response  = await agent.inference(user_msg)
        while response.tool_call:
            result = call_tools(response.tool_calls)
            response = await agent.inference(f"The result of the tool calls is: {result}")
        print(response.response)


asyncio.run(main())