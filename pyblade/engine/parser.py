import html
import re

from .contexts import LoopContext
from .exceptions import UndefinedVariableError


class Parser:

    def __init__(self):
        self.directives = {
            "for": self._parse_for,
            "if": self._parse_if,
        }

    def parse(self, template: str, context: dict) -> str:
        """
        Parse template to replace directives by the real values

        :param template:
        :param context:
        :return:
        """

        # Start parsing directives cause some directives like the @for loop may have
        # local context variables that are not global and could raise UndefinedVariableError
        template = self.parse_directives(template, context)
        template = self.parse_variables(template, context)

        return template

    def parse_variables(self, template: str, context: dict) -> str:
        """Parse all variables within a template"""

        template = self._render_escaped_variables(template, context)
        template = self._render_unescaped_variables(template, context)
        return template

    def parse_directives(self, template: str, context: dict) -> str:
        """Process all directives within a template."""

        for directive, func in self.directives.items():
            template = func(template, context)

        return template

    def _render_escaped_variables(self, template: str, context: dict) -> str:
        """Match variables in {{ }} and replace them with the escaped values"""

        return re.sub(
            r"{{\s*(.*?(?:\.?.*?)*)\s*}}", lambda match: self._replace_variable(match, context, escape=True), template
        )

    def _render_unescaped_variables(self, template: str, context: dict) -> str:
        """Match variables in {!! !!} and replace them with the unescaped values"""

        return re.sub(
            r"{!!\s*(.*?(?:\.?.*?)*)\s*!!}",
            lambda match: self._replace_variable(match, context, escape=False),
            template,
        )

    def _replace_variable(self, match, context, escape: bool) -> str:
        expression = match.group(1).split(".")
        variable_name = expression[0]

        if variable_name not in context:
            raise UndefinedVariableError(f"Undefined variable '{variable_name}' on line {self._get_line_number(match)}")

        # If expression contains dots (e.g.: var.upper() or loop.index, ...), evaluate it
        if len(expression) > 1:
            variable_value = eval(".".join(expression), {}, context)
        else:
            variable_value = context[variable_name]

        if escape:
            return html.escape(str(variable_value))
        return str(variable_value)

    def _get_line_number(self, match) -> int:
        """
        Get the line number where a variable is located in the template.
        Useful for debug.
        """

        return match.string.count("\n", 0, match.start()) + 1

    def _parse_if(self, template, context):
        """Handle @if, @elif, @else and @endif directives."""

        pattern = re.compile(
            r"@(if)\s*\((.*?)\)\s*(.*?)\s*(?:@(elif)\s*\((.*?)\)\s*(.*?))*(?:@(else)\s*(.*?))?@(endif)", re.DOTALL
        )
        return pattern.sub(lambda match: self._handle_if(match, context), template)

    def _handle_if(self, match, context):

        captures = [group for group in match.groups() if group not in (None, "")]

        for i, capture in enumerate(captures[:-1]):
            if capture in ("if", "elif", "else"):
                if capture in ("if", "elif"):
                    if eval(captures[i + 1], {}, context):
                        return captures[i + 2]
                else:
                    return captures[i + 1]

    def _parse_for(self, template, context):
        """Handle @for, @empty and @endfor directives."""

        pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor", re.DOTALL)
        return pattern.sub(lambda match: self._handle_for(match, context), template)

    def _handle_for(self, match, context):
        """Executes the for logic."""

        variable = match.group(1)
        iterable = eval(match.group(2), {}, context)
        block = match.group(3)
        empty_block = match.group(4)

        # Empty handling if iterable is None or empty
        if iterable is None or len(iterable) == 0:
            return empty_block if empty_block else ""

        result = []
        loop = LoopContext(iterable)
        for (
            index,
            item,
        ) in enumerate(iterable):
            loop.index = index

            local_context = {
                **context,
                variable: item,
                "loop": loop,
            }

            r_block = self._parse_if(block, local_context)
            r_block = self._render_escaped_variables(r_block, local_context)
            r_block = self._render_unescaped_variables(r_block, local_context)

            result.append(r_block)
        return "".join(result)
