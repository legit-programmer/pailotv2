import subprocess
import shlex

def execute_command(cmd: str):
    result = subprocess.run(
        shlex.split(cmd),
        capture_output=True,
        text=True
    )

    return {
        "stdout":result.stdout,
        "stderr":result.stderr,
        "exit_code":result.returncode
    }

def write_file(path: str, data):
    with open(path, 'w') as f:
        f.write(data)
        
def read_file(path: str):
    with open(path, 'r') as f:
        return f.read()