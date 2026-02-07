import subprocess
import shlex
from models.model_tools import add_tool, Tool, ToolArgument, get_model_tools


def execute_command(cmd: str):
    result = subprocess.run(
        shlex.split(cmd),
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
