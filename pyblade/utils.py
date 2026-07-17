import re
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List, Optional, Tuple

from pyblade.cli.exceptions import CommandError


def get_version(package_name: str = "pyblade"):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return


def split_dotted_path(dotted: str) -> Tuple:
    """
    :param: The path in dot format (e.g: 'path.to.some.file)
    :returns: A tuple containing the path and the file name
    """
    parts = dotted.split(".")
    path = ""
    if len(parts) > 1:
        path = Path(*parts[:-1])
    return (path, parts[-1])


def run_command(command: List[str] | str, cwd: Optional[Path] = None) -> None:
    if isinstance(command, str):
        command = command.split(" ")

    if not cwd:
        cwd = Path.cwd()
    try:
        result = subprocess.check_call(command, text=True, cwd=cwd)
        return result
    except Exception as e:
        raise CommandError(str(e))


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

    # Falback to CWD if no pyblade.json file was found
    return current


def validate_single_root_node(html_content: str):
    """
    Validate that an HTML component template has a single root node.

    Args:
        html_content (str): HTML content as a string

    Returns:
        bool: True if single root node, False otherwise
    """

    # Remove all comments first
    html_content = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"{#(.*?)#}", "", html_content, flags=re.DOTALL)
    html_content = re.sub(r"@comment\s*(?P<content>.*?)@endcomment", "", html_content, flags=re.DOTALL)

    # Count tags
    tags = []
    depth = 0

    # Simple state machine to track tag depth
    for match in re.finditer(r"<(/)?(\w+)[^>]*>", html_content):
        is_closing = match.group(1) == "/"
        tag = match.group(2)

        if not is_closing:
            depth += 1
            if depth == 1:
                tags.append(tag)
        else:
            depth -= 1

    # Ignore single-tag templates or templates with only whitespace
    if len(tags) <= 1:
        return True

    return False
