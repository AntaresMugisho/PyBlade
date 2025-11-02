"""
Core template processing functionality.
"""

import html
from typing import Any, Dict

from pyblade.config import settings

from .cache import TemplateCache
from .contexts import LoopContext
from .evaluator import ExpressionEvaluator
from .lexer import Lexer
from .nodes import ForNode, IfNode, Node, TextNode, VarNode
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
        self.context = context

        # Check cache first
        cached_result = self.cache.get(template, context)
        if cached_result is not None:
            return cached_result

        try:
            lexer = Lexer(template)
            tokens = lexer.tokenize()

            parser = Parser(tokens)
            ast = parser.parse()

            output = []
            for node in ast:
                result = self.render_node(node)
                if result is not None:
                    output.append(str(result))

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

    def eval(self, expression: str, context: Dict[str, Any]) -> Any:
        evaluator = ExpressionEvaluator(context)
        return evaluator.evaluate(expression)

    # Directive renderers

    def render_node(self, node: Node) -> str:
        """Render a single node"""
        if isinstance(node, TextNode):
            return node.content

        elif isinstance(node, VarNode):
            return self.render_variable(node)

        elif isinstance(node, IfNode):
            return self.render_if(node)

        elif isinstance(node, ForNode):
            return self.render_for(node)

        return ""

    # RENDERER FUNCTIONS
    def render_variable(self, node: Node):
        try:
            # Use ExpressionEvaluator for method chaining support
            evaluator = ExpressionEvaluator(self.context)
            result = evaluator.evaluate(node.expression)

            # Convert wrapper objects to strings
            result_str = str(result)

            # Auto-escape HTML unless it's raw interpolation
            if node.escaped:
                return html.escape(result_str)
            else:
                return result_str

        except Exception as e:
            return f"<!-- Error rendering '{node.expression}': {e} -->"

    def render_if(self, node: IfNode) -> str:
        """Process @if, @elif, and @else directives."""

        try:
            condition_result = self.eval(node.condition, self.context)
            if condition_result:
                output = []
                for child_node in node.body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)
            else:
                found_elif = False
                for elif_cond, elif_body in node.elif_blocks:
                    elif_condition_result = self.eval(elif_cond, self.context)
                    if elif_condition_result:
                        output = []
                        for child_node in elif_body:
                            result = self.render_node(child_node)
                            if result:
                                output.append(result)
                        return "".join(output)
                        found_elif = True
                        break
                if not found_elif and node.else_body:
                    output = []
                    for child_node in node.else_body:
                        result = self.render_node(child_node)
                        if result:
                            output.append(result)
                    return "".join(output)
        except Exception as e:
            return f"<!-- Error evaluating if condition '{node.condition}': {e} -->"

        return ""

    def render_for(self, node: ForNode) -> str:
        try:
            from .wrappers import wrap_value

            iterable = self.eval(node.collection_expr, self.context)
            if not isinstance(iterable, (list, tuple, set, dict)):
                raise TypeError(f"'{node.collection_expr}' is not iterable.")

            if not iterable and node.empty_body:
                output = []
                for child_node in node.empty_body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)
                return "".join(output)

            # Ensure collection is iterable for iteration
            items_to_iterate = list(iterable.items()) if isinstance(iterable, dict) else list(iterable)

            # Backup potential variable name in the context
            old_value = self.context.get(node.item_var)
            old_loop = self.context.get("loop")

            loop = LoopContext(items_to_iterate, parent=old_loop)

            output = []
            for i, item in enumerate(items_to_iterate):
                loop.index = i
                wrapped_item = wrap_value(item)
                self.context[node.item_var] = wrapped_item
                self.context["loop"] = loop

                for child_node in node.body:
                    result = self.render_node(child_node)
                    if result:
                        output.append(result)

            # Restore old values
            if old_value is not None:
                self.context[node.item_var] = old_value
            else:
                self.context.pop(node.item_var, None)

            if old_loop is not None:
                self.context["loop"] = old_loop
            else:
                self.context.pop("loop", None)

            return "".join(output)

        except Exception as e:
            return f"<!-- Error evaluating for loop '{node.collection_expr}': {e} -->"
