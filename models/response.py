from pydantic import BaseModel

class ToolCall(BaseModel):
    tool_name: str
    args: dict

class Response(BaseModel):
    tool_call: bool = False
    tool_calls: list[ToolCall] | None = None
    response: str | None = None
