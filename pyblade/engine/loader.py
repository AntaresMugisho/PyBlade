"""
Template file loading functionality.
"""

from pathlib import Path
from typing import List, Optional, Union

from .exceptions import TemplateNotFoundError
from .template import Template


class TemplateLoader:
    """Handles loading template files from the filesystem."""

    def __init__(self, template_dirs: Optional[List[Union[str, Path]]] = None):
        """
        Initialize the template loader.

        Args:
            template_dirs: List of template directories
        """
        self._template_dirs = []
        self._extension = ".html"
        if template_dirs:
            self.add_directories(template_dirs)

    def add_directories(self, directories: List[Union[str, Path]]) -> None:
        """
        Add template directories to the search path.

        Args:
            directories: List of directory paths
        """
        for directory in directories:
            path = Path(directory)
            if path.is_dir():
                self._template_dirs.append(path)

    def load_template(self, template_name: str) -> Template:
        """
        Load a template file by name.

        Args:
            template_name: Name of the template to load

        Returns:
            The template content

        Raises:
            TemplateNotFoundError: If the template file cannot be found
        """

        # Remove extension if it exists
        template_name = template_name.removesuffix(self._extension)

        # Convert dot notation to path
        template_path = template_name.replace(".", "/")

        # Search in all template directories
        for directory in self._template_dirs:
            full_path = directory / f"{template_path}{self._extension}"
            try:
                content = self._read_template(full_path)

                return Template(template_name, full_path, content)
            except (IOError, OSError):
                continue

        raise TemplateNotFoundError(f"{template_name}{self._extension}")

    def _read_template(self, path: Path) -> str:
        """
        Read a template file.

        Args:
            path: Path to the template file

        Returns:
            The template content

        Raises:
            IOError: If there's an error reading the file
        """
        if not path.is_file():
            raise IOError(f"Not a file: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise IOError(f"Error reading template file {path}: {str(e)}")


# Global loader instances
_default_loader = TemplateLoader()


def load_template(template_name: str, directories: Optional[List[Union[str, Path]]] = None, engine=None) -> Template:
    """
    Load a template using the default loader.

    Args:
        template_name: Name of the template to load
        directories: Optional list of template directories

    Returns:
        The template content

    Raises:
        TemplateNotFoundError: If the template file cannot be found
    """

    if directories:
        _default_loader.add_directories(directories)
    return _default_loader.load_template(template_name)
