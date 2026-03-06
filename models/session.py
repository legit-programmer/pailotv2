from langchain.messages import SystemMessage
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    session_id: str
    base_prompt: SystemMessage | None = None
    model: str

class Session(BaseModel):
    session_id: str
    model: str
    messages: list = []