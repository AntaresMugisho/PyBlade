import subprocess
from pathlib import Path


def command(command: str) -> None:

    commands = command.split(" ")

    try:
        subprocess.check_call(commands, cwd=Path("my_project"))
    except subprocess.CalledProcessError as e:
        raise Exception(f"Command failed with exit code {e.returncode}")
