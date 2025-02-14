import subprocess
from pathlib import Path
from typing import List, Optional


class RunError(Exception):
    def __init__(self, exception) -> None:
        super().__init__(exception)

        if hasattr(exception, "__dict__"):
            self.__dict__.update(exception.__dict__)


def run(command: List[str] | str, cwd: Optional[Path] = None) -> None:
    if isinstance(command, str):
        command = command.split(" ")

    if not cwd:
        cwd = Path.cwd()
    try:
        result = subprocess.check_call(command, text=True, cwd=cwd)
        return result
    except subprocess.CalledProcessError as e:
        raise RunError(e)
