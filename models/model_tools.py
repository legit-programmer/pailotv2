from pydantic import BaseModel


class ToolArgument(BaseModel):
    name: str
    type: str
    description: str


class Tool(BaseModel):
    name: str
    description: str
    args: list[ToolArgument] | None = None


class ModelTools(BaseModel):
    tools: list[Tool]


all_tools = None


def get_model_tools():
    global all_tools
    if not isinstance(all_tools, ModelTools):
        all_tools = ModelTools(tools=[])
    return all_tools


def add_tool(tool: Tool):
    get_model_tools().tools.append(tool)
