"""
PyBlade template rendering engine.
"""

from pathlib import Path
from typing import Dict, List, Optional

from pyblade.config import settings
from pyblade.engine.exceptions import PyBladeException, UndefinedVariableError

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
        self._debug = None
        self.framework = settings.framework

    @property
    def debug(self) -> bool:
        """Auto-detect DEBUG mode from framework if not explicitly set."""
        if self._debug is not None:
            return self._debug

        # Auto-detect from framework
        if self.framework == "django":
            try:
                from django.conf import settings

                return settings.DEBUG
            except Exception:
                return False
        elif self.framework == "flask":
            try:
                from flask import current_app

                return current_app.debug
            except Exception:
                return False
        elif self.framework == "fastapi":
            # FastAPI doesn't have built-in DEBUG, check environment
            import os

            return os.getenv("DEBUG", "False").lower() == "true"

        return False

    def _handle_error(
        self, error: Exception, template_name: str = None, template_source: str = None, context: dict = None
    ) -> str:
        """Handle rendering errors and return appropriate error page."""

        if self.debug:
            return self._render_debug_error(error, template_name, template_source, context)
        else:
            return self._render_production_error(error)

    def _render_debug_error(
        self, error: Exception, template_name: str = None, template_source: str = None, context: dict = None
    ) -> str:
        """Render detailed debug error page."""

        # Extract error details
        error_type = type(error).__name__
        error_message = str(error)
        line_number = getattr(error, "line_number", None)

        # Get code context if we have line number and source
        code_lines = []
        if template_source and line_number:
            lines = template_source.split("\n")
            start = max(0, line_number - 3)
            end = min(len(lines), line_number + 3)

            for i in range(start, end):
                code_lines.append(
                    {"number": i + 1, "content": lines[i] if i < len(lines) else "", "is_error": (i + 1) == line_number}
                )

        # Get suggestions based on error type
        suggestions = self._get_error_suggestions(error)

        # Render error template
        context = {
            "error_type": error_type,
            "error_message": error_message,
            "template_name": template_name or "Unknown",
            "line_number": line_number,
            "code_lines": code_lines,
            "suggestions": suggestions,
        }

        from pprint import pprint

        pprint(context)

        template = loader.load_template("error", [Path(__file__).parent / "templates"])
        return template.render(context)

    def _get_error_suggestions(self, error: Exception) -> list:
        """Get helpful suggestions based on error type."""
        suggestions = []

        if isinstance(error, (NameError, UndefinedVariableError)):
            suggestions.append(
                {
                    "title": "Variable Not Found",
                    "message": "Check if the variable is defined in your template context.",
                }
            )
            if hasattr(error, "available_vars") and error.available_vars:
                suggestions.append(
                    {
                        "title": "Available Variables",
                        "message": f"Available: {', '.join(error.available_vars[:10])}",
                    }
                )

        elif isinstance(error, AttributeError):
            suggestions.append(
                {
                    "title": "Attribute Error",
                    "message": "The object does not have this attribute. Check the object type and available methods.",
                }
            )

        elif isinstance(error, TypeError):
            suggestions.append(
                {
                    "title": "Type Error",
                    "message": "Check that you are calling methods correctly and passing the right types.",
                }
            )

        return suggestions

    def render(
        self,
        template: str,
        context: Optional[Dict] = None,
        template_name: Optional[str] = None,
        template_path: Optional[Path] = None,
    ) -> str:
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

        try:
            template = self._processor.render(template, context)
        except PyBladeException as e:
            return self._handle_error(error=e, template_source=template, template_name=template_path, context=context)

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
