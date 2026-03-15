import inspect
import subprocess
from mcps.mcp_manager import MCPManager
from models.model_tools import add_tool, Tool, ToolArgument, get_model_tools
from models.response import Response, ToolCall
from langchain_google_genai import ChatGoogleGenerativeAI


def execute_command(cmd: str):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode
    }


def write_file(path: str, data):
    with open(path, 'w') as f:
        f.write(data)


def read_file(path: str):
    with open(path, 'r') as f:
        return f.read()


def configure_all_tools():
    print("Configuring tools...")
    # for now, tools are defined locally in agent/agent.py and registered with the MCP manager when the agent is initialized. In the future, we can move tool definitions to separate files in the tools directory and dynamically load them here.
    
        # add_tool(Tool(
        #     name="execute_command",
        #     description="Executes a shell command and returns the output, error and exit code.",
        #     args=[
        #         ToolArgument(name="cmd", type="str",
        #                      description="The command to execute")
        #     ]
        # ))

        # add_tool(Tool(
        #     name="write_file",
        #     description="Writes data to a file at the specified path.",
        #     args=[
        #         ToolArgument(name="path", type="str",
        #                      description="The path to the file"),
        #         ToolArgument(name="data", type="str",
        #                      description="The data to write to the file")
        #     ]
        # ))

        # add_tool(Tool(
        #     name="read_file",
        #     description="Reads the contents of a file at the specified path and returns it.",
        #     args=[
        #         ToolArgument(name="path", type="str",
        #                      description="The path to the file")
        #     ]
        # ))


async def call_tool(tool_name: str, args: dict, tool_map: dict):
    if tool_name not in tool_map:
        raise ValueError(f"Tool {tool_name} not found")
    
    func = tool_map[tool_name]
    if inspect.iscoroutinefunction(func):
        return await func(**args)
    else:
        return func(**args)


async def call_tools(tool_calls: list[ToolCall], agent):
    tool_map = agent.tool_map
    mcp_manager = agent.mcp_manager

    if not tool_map:
        print("No tool map, skipping tool calls")
        return []
    results = []
    print(f"Received tool calls: {[{'tool_name': tc.tool_name, 'args': tc.args} for tc in tool_calls]}")
    for tool_call in tool_calls:
        tool_name = tool_call.tool_name
        args = tool_call.args
        result = None
        
        try:
            if mcp_manager:
                result = await mcp_manager.call_tool(tool_name, args)
            if not result:
                result = await call_tool(tool_name, args, tool_map=tool_map)
        except Exception as e:
            result = f"Error calling tool {tool_name}: {e}"
            


        results.append({
            "tool_name": tool_name,
            "result": result
        })

    return results

