import re
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


def pascal_to_snake(string: str) -> str:
    """Convert a PascalCased string to snake_cased string"""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", string)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower().replace("-", "_")


def snakebab_to_pascal(string: str) -> str:
    """Converts a snake_cased or kebab-cased string to PascalCased string"""
    return string.title().replace("_", "").replace("-", "")


def get_project_root():
    """Find the project root directory by looking for pyblade.json."""
    current = Path.cwd()

    for directory in [current, *current.parents]:
        if (directory / "pyblade.json").exists():
            return directory
    raise Exception(f"Not a PyBlade project (or any parent up to mount point {current.parents[-1]})")
