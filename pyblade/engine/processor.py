"""
Core template processing functionality.
"""

from typing import Any, Dict

from .cache import TemplateCache
from .lexer import Lexer
from .parser import Parser
from . import loader


class TemplateProcessor:
    """
    Main template processing class that coordinates parsing, caching,
    and rendering of templates.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600, debug: bool = None, framework: str = None):
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.context = {}

    def render(
        self, template: str, context: Dict[str, Any], template_name: str = None, template_path: str = None
    ) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary
            template_name: Optional name of the template file

        Returns:
            The rendered template

        Raises:
            TemplateRenderError: If there's an error during rendering
        """

        self.context = context.copy() if context else {}

        # Check cache first
        cached_result = self.cache.get(template, self.context)
        if cached_result is not None:
            return cached_result

        try:
            tokens = Lexer(template).tokenize()
            nodes = Parser(tokens).parse()

            # First pass: render the template to collect sections/blocks
            output = []
            for node in nodes:
                rendered = node.render(self.context)
                if rendered is not None:
                    output.append(str(rendered))

            result = "".join(output)

            # Check if this template extends another
            if "__extends" in self.context:
                layout_path = self.context["__extends"]
                # Load and render the parent layout with the collected sections/blocks
                # layout_template = loader.load_template(layout_path)
                # # Remove the __extends key to avoid infinite recursion
                # extends_context = self.context.copy()
                # del extends_context["__extends"]
                # result = layout_template.render(extends_context)

            # Save cache
            self.cache.set(template, self.context, result)

            return result

        except Exception as e:
            raise e

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self.cache.clear()

    def invalidate_template(self, template: str, context: Dict[str, Any]) -> None:
        """
        Invalidate a specific template in the cache.

        Args:
            template: The template string
            context: The context dictionary
        """
        self.cache.invalidate(template, context)
