from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import asyncio
from dotenv import load_dotenv

load_dotenv()

class Agent:
    def __init__(self, tools, model_name):
        self.messages = []
        self.tools = tools
        self.model_name = model_name
        self.llm = None

    def initialize_openai(self):
        self.llm  = ChatOpenAI(model=self.model_name)

    async def inference(self, message: str):
        self.messages.append(HumanMessage(message))
        response = await self.llm.ainvoke(self.messages)
        response = response.content[0]
        self.messages.append(AIMessage(response))
        return response
    


async def main():
    agent = Agent(None, 'gpt-4o')
    agent.initialize_openai()
    while True:
        user_msg = input(">")
        print(await agent.inference(user_msg))


asyncio.run(main())