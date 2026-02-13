import subprocess
import shlex
from models.model_tools import add_tool, Tool, ToolArgument, get_model_tools
from models.response import Response, ToolCall


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
    add_tool(Tool(
        name="execute_command",
        description="Executes a shell command and returns the output, error and exit code.",
        args=[
            ToolArgument(name="cmd", type="str",
                         description="The command to execute")
        ]
    ))

    add_tool(Tool(
        name="write_file",
        description="Writes data to a file at the specified path.",
        args=[
            ToolArgument(name="path", type="str",
                         description="The path to the file"),
            ToolArgument(name="data", type="str",
                         description="The data to write to the file")
        ]
    ))

    add_tool(Tool(
        name="read_file",
        description="Reads the contents of a file at the specified path and returns it.",
        args=[
            ToolArgument(name="path", type="str",
                         description="The path to the file")
        ]
    ))

tool_map = {
    "execute_command": execute_command,
    "write_file": write_file,
    "read_file": read_file
}

def call_tool(tool_name: str, args: dict):
    if tool_name not in tool_map:
        raise ValueError(f"Tool {tool_name} not found")
    print(f"Calling tool {tool_name} with args {args}")
    confirm = input("Press Enter to continue...")
    if confirm.lower() == "exit":
        print("Exiting...")
        exit(0)
    return tool_map[tool_name](**args)

def call_tools(tool_calls: list[ToolCall]):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.tool_name
        args = tool_call.args
        result = call_tool(tool_name, args)
        results.append({
            "tool_name": tool_name,
            "result": result
        })
    return results

