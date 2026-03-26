from pathlib import Path
from typing import Dict, List, Optional

from pyblade.config import settings
from pyblade.engine.exceptions import PyBladeException

from . import loader
from .processor import TemplateProcessor


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

    def _handle_error(
        self,
        error: PyBladeException,
        template_source: str = None,
        template_path: Path = None,
    ) -> str:
        """Handle rendering errors and return error page."""

        line = error.line

        code_lines = []
        if template_source and line:
            lines = template_source.split("\n")

            start = max(0, line - 4)
            end = min(len(lines), line + 3)

            for i in range(start, end):
                code_lines.append(
                    {
                        "number": i + 1,
                        "content": lines[i] if i < len(lines) else "",
                        "is_error": (i + 1) == line,
                    }
                )

        context = {
            "error_type": type(error).__name__,
            "error_message": error.message,
            "template_path": template_path,
            "line": line,
            "code_lines": code_lines,
            "help": error.help
            or "An unexpected error occurred during template rendering. "
            "Check the full stack trace to identify the origin.",
        }

        template = loader.load_template("error", [Path(__file__).parent / "templates"])

        return template.render(context)

    def render(
        self,
        template: str,
        context: Optional[Dict] = None,
        template_path: Optional[Path] = None,
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary
            template_path: The full path to teh template file

        Returns:
            The rendered template string
        """

        if context is None:
            context = {}

        try:
            template = self._processor.render(template, context)
        except PyBladeException as exc:
            if settings.DEBUG:

                if exc.template:
                    template = exc.template.content
                    template_path = exc.template.path
                return self._handle_error(error=exc, template_source=template, template_path=template_path)

            raise exc

        except Exception as exc:
            raise exc

        return template

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

        template = loader.load_template(template_name, self._template_dirs, self)
        return template

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
