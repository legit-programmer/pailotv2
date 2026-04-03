import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.operating_system = os.getenv("OS", "Unknown OS")
        self.discord_master_user_id = int(os.getenv("DISCORD_MASTER_USER_ID"))
        self.gateway_port=os.getenv("GATEWAY_PORT", "8000")


config = None

def get_config():
    global config
    if not config:
        config = Config()
    return config
