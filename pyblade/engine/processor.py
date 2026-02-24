"""
Core template processing functionality.
"""

from typing import Any, Dict

from pyblade.config import settings

from .cache import TemplateCache
from .lexer import Lexer
from .parser import Parser


class TemplateProcessor:
    """
    Main template processing class that coordinates parsing, caching,
    and rendering of templates.
    """

    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600, debug: bool = None, framework: str = None):
        self.cache = TemplateCache(max_size=cache_size, ttl=cache_ttl)
        self.framework = settings.framework  # 'django', 'fastapi', 'flask', or None
        self._debug = debug
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
        # Wrap context values once so templates see rich, chainable variables
        from .wrappers import wrap_value

        self.context = {k: wrap_value(v) for k, v in (context or {}).items()}

        # Check cache first
        cached_result = self.cache.get(template, context)
        if cached_result is not None:
            return cached_result

        try:
            tokens = Lexer(template).tokenize()
            nodes = Parser(tokens).parse()

            output = []
            for node in nodes:
                rendered = node.render(self.context)
                if rendered is not None:
                    output.append(str(rendered))

            result = "".join(output)

            # Save cache
            self.cache.set(template, context, result)

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
