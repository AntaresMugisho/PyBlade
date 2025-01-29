"""
Template class for representing loaded templates.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

from .parsing.template_processor import TemplateProcessor

try:
    from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy

    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False


class Template:
    """Represents a loaded template file."""

    def __init__(
        self,
        template_name: str,
        template_path: Union[str, Path],
        template_string: Optional[str] = None,
        backend: Optional[Any] = None,
        engine: Optional[Any] = None,
    ):
        """
        Initialize a template.

        Args:
            template_name: Name of the template
            template_path: Path to the template file
            template_string: The template content
            backend: Optional template backend
            engine: Optional template engine
        """
        self.name = template_name
        self.path = Path(template_path)
        self.content = template_string
        self.backend = backend
        self.engine = engine

    def __str__(self) -> str:
        """Return the template content."""
        return self.content or ""

    def render(self, context: Optional[Dict[str, Any]] = None, request: Optional[Any] = None) -> str:
        """
        Render the template with the given context.

        Args:
            context: The context dictionary
            request: Optional request object (for Django integration)

        Returns:
            The rendered template

        Raises:
            ValueError: If no engine is set
        """

        if context is None:
            context = {}
            
        # Handle Django-specific context if available
        if request is not None and DJANGO_AVAILABLE:
            context["request"] = request
            context["csrf_input"] = csrf_input_lazy(request)
            context["csrf_token"] = csrf_token_lazy(request)

            if self.backend and hasattr(self.backend, "template_context_processors"):
                for processor in self.backend.template_context_processors:
                    context.update(processor(request))

        if not self.engine:
            self._processor = TemplateProcessor()
            return self._processor.render(self.content, context)

        return self.engine.render(self.content, context)

    def get_relative_path(self, base_dir: Optional[Union[str, Path]] = None) -> str:
        """
        Get the template path relative to a base directory.

        Args:
            base_dir: Optional base directory path

        Returns:
            The relative path as a string
        """
        if base_dir:
            try:
                return str(self.path.relative_to(base_dir))
            except ValueError:
                pass
        return str(self.path)

    def set_engine(self, engine):
        self.engine = engine

    def set_backend(self, backend):
        self.backend = backend
