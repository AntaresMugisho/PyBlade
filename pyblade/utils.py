import os
import re
import subprocess

# import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List, Optional, Tuple

from pyblade.cli.exceptions import RunError
from pyblade.config import settings


def get_version(package_name: str = "pyblade"):
    try:
        return version(package_name)
    except PackageNotFoundError:
        print("'{package_name}' is not installed via pip")
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
    except subprocess.CalledProcessError as e:
        raise RunError(e)


def run_django_command(command: List[str] | str, cwd: Optional[Path] = None) -> None:
    if isinstance(command, str):
        command = command.split(" ")

    root_dir = get_project_root()
    if command[0] != "manage.py":
        command = [str(root_dir / "manage.py")] + command

    if not cwd:
        cwd = Path.cwd()

    # sys.path.insert(0, str(root_dir)) # MUST BE PASSED AS STRING
    settings_path_wo_ext = os.path.splitext(settings.settings_path)[0]
    settings_module = settings_path_wo_ext.replace("/", ".")
    os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    print(f"Running Django command: {' '.join(command)} in {cwd or root_dir}")
    execute_from_command_line(command)


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


def setup_django():
    pass
