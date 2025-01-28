"""
Variable parsing and handling for the template engine.
"""

import html
import re
from typing import Any, Dict, Match, Pattern

from ..contexts import AttributesContext, ClassContext, SlotContext
from ..exceptions import UndefinedVariableError


class VariableParser:
    """Handles parsing and rendering of template variables."""

    # Cached regex patterns
    _ESCAPED_VAR_PATTERN: Pattern = re.compile(r"{{\s*(.*?)\s*}}")
    _UNESCAPED_VAR_PATTERN: Pattern = re.compile(r"{!!\s*(.*?)\s*!!}")

    def __init__(self):
        self._context: Dict[str, Any] = {}
        self.initial_template: str = ""

    def parse_variables(self, template: str, context: Dict[str, Any]) -> str:
        """
        Parse all variables within a template.

        Args:
            template: The template string
            context: The context dictionary

        Returns:
            The template with all variables replaced
        """
        self._context = context
        template = self._render_escaped_variables(template)
        template = self._render_unescaped_variables(template)

        return template

    def _render_escaped_variables(self, template: str) -> str:
        """
        Replace variables in {{ }} with escaped values.

        Args:
            template: The template string

        Returns:
            The template with escaped variables replaced
        """
        return self._ESCAPED_VAR_PATTERN.sub(lambda match: self._replace_variable(match, escape=True), template)

    def _render_unescaped_variables(self, template: str) -> str:
        """
        Replace variables in {!! !!} with unescaped values.

        Args:
            template: The template string

        Returns:
            The template with unescaped variables replaced
        """
        return self._UNESCAPED_VAR_PATTERN.sub(lambda match: self._replace_variable(match, escape=False), template)

    def _replace_variable(self, match: Match, escape: bool) -> str:
        """
        Replace a variable with its value from the context.

        Args:
            match: The regex match object
            escape: Whether to HTML escape the value

        Returns:
            The replaced variable value

        Raises:
            UndefinedVariableError: If the variable is not found in context
        """
        expression = match.group(1)

        if not expression:
            return ""

        if expression.startswith("."):
            raise UndefinedVariableError(
                f"Variable name should not start with '.' on line {self._get_line_number(match)}"
            )

        expression = expression.split(".")
        variable_name = expression[0]

        if variable_name not in self._context:
            raise UndefinedVariableError(f"Undefined variable '{variable_name}' on line {self._get_line_number(match)}")

        # Handle nested attributes and method calls
        if len(expression) > 1:
            try:
                variable_value = eval(".".join(expression), {}, self._context)
            except Exception as e:
                raise UndefinedVariableError(f"Error evaluating expression '{'.'.join(expression)}': {str(e)}")
        else:
            variable_value = self._context[variable_name]

        # Special context objects are never escaped
        if isinstance(variable_value, (SlotContext, AttributesContext, ClassContext)):
            escape = False

        # Convert to string and escape if needed
        result = str(variable_value)
        return html.escape(str(result)) if escape else str(result)

    def _get_line_number(self, match: Match) -> int:
        """Get the line number for a position in the template."""
        return self.initial_template.count("\n", 0, match.start()) + 1
