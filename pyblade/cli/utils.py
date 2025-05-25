import subprocess
from pathlib import Path
from typing import List, Optional

from pyblade.cli.exceptions import RunError


def run_command(command: List[str] | str, cwd: Optional[Path] = None) -> None:
    if isinstance(command, str):
        command = command.split(" ")

    if not cwd:
        cwd = Path.cwd()
    try:
        result = subprocess.check_call(command, text=True, cwd=cwd)
        return result
    except subprocess.CalledProcessError as e:
        raise RunError(e)
