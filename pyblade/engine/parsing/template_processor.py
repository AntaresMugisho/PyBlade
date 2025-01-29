"""
Core template processing functionality.
"""

from typing import Any, Dict

from ..exceptions import TemplateRenderingError
from .cache import TemplateCache
from .directives import DirectiveParser
from .variables import VariableParser


class TemplateProcessor:
    """
    Main template processing class that coordinates parsing, caching,
    and rendering of templates.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600):
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.directive_parser = DirectiveParser()
        self.variable_parser = VariableParser()

    def render(self, template: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template: The template string to render
            context: The context dictionary

        Returns:
            The rendered template

        Raises:
            TemplateRenderingError: If there's an error during rendering
        """
        try:
            # Check cache first
            cached_result = self.cache.get(template, context)
            if cached_result is not None:
                return cached_result

            # Set the original template before processing to handle line numbers on template parsing error
            self.directive_parser.initial_template = template
            self.variable_parser.initial_template = template

            # Process template
            result = self._process_template(template, context)

            # Cache the result
            self.cache.set(template, context, result)

            return result

        except Exception as e:
            raise TemplateRenderingError(f"Error rendering template: {str(e)}")

    def _process_template(self, template: str, context: Dict[str, Any]) -> str:
        """
        Process a template by parsing directives and variables.

        Args:
            template: The template string
            context: The context dictionary

        Returns:
            The processed template
        """
        # First process all directives
        template = self.directive_parser.parse_directives(template, context)

        # Then process variables
        template = self.variable_parser.parse_variables(template, context)

        return template

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
