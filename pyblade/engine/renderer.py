"""
PyBlade template rendering engine.
"""

from typing import Dict, List, Optional

from . import loader
from .exceptions import TemplateNotFoundError
from .parsing.template_processor import TemplateProcessor


class PyBlade:
    """Main template rendering engine class."""

    def __init__(self, dirs: Optional[List[str]] = None, cache_size: int = 1000, cache_ttl: int = 3600):
        """
        Initialize the PyBlade template engine.

        Args:
            dirs: List of template directories
            cache_size: Maximum number of templates to cache
            cache_ttl: Cache time-to-live in seconds
        """
        self._template_dirs = dirs or []
        self._processor = TemplateProcessor(cache_size=cache_size, cache_ttl=cache_ttl)

    def render(self, template: str, context: Optional[Dict] = None) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary

        Returns:
            The rendered template string
        """

        if context is None:
            context = {}

        return self._processor.render(template, context)

    def render_file(self, template_name: str, context: Optional[Dict] = None) -> str:
        """
        Load and render a template file.

        Args:
            template_name: Name of the template file
            context: The context dictionary

        Returns:
            The rendered template

        Raises:
            TemplateNotFoundError: If the template file cannot be found
        """
        template = self.get_template(template_name)
        return self.render(template.content, context)

    def get_template(self, template_name: str) -> str:
        """
        Load a template file by name.

        Args:
            template_name: Name of the template file

        Returns:
            The template content

        Raises:
            TemplateNotFoundError: If the template file cannot be found
        """
        try:
            template = loader.load_template(template_name, self._template_dirs, self)
            return template
        except Exception as e:
            raise TemplateNotFoundError(template_name) from e

    def from_string(self, template_code, context):
        pass

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._processor.clear_cache()

    def invalidate_template(self, template: str, context: Optional[Dict] = None) -> None:
        """
        Invalidate a specific template in the cache.

        Args:
            template: The template string
            context: The context dictionary used with the template
        """
        if context is None:
            context = {}
        self._processor.invalidate_template(template, context)
