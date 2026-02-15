import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")


config = None

def get_config():
    global config
    if not config:
        config = Config()
    return config