from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Tuple


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
