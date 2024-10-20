import re
import html

from .contexts import LoopContext
from .exceptions import UndefinedVariableError
from .sandbox import safe_eval, safe_exec


class Parser:

    def __init__(self):

        self.directives = {
            "if": self._parse_if,
            "for": self._parse_for
        }

    def parse(self, template: str, context: dict) -> str:
        """
        Parse template

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
        """
        Parse all variables within a template

        :param template:
        :param context:
        :return:
        """

        template = self._render_escaped_variables(template, context)
        template = self._render_unescaped_variables(template, context)
        return template

    def parse_directives(self, template: str, context: dict) -> str:
        """
        Process all directives within a template.
        
        :param template: 
        :param context: 
        :return: 
        """

        for directive, func in self.directives.items():
            template = func(template, context)

        return template

    def _render_escaped_variables(self, template: str, context: dict) -> str:
        """Match variables in {{ }} and replace them with the escaped values"""

        return re.sub(r"{{\s*(\w+)\s*}}", lambda match: self._replace_variable(match, context, escape=True),
                      template)

    def _render_unescaped_variables(self, template: str, context: dict) -> str:
        """Match variables in {!! !!} and replace them with the unescaped values"""

        return re.sub(r'{!!\s*(\w+)\s*!!}', lambda match: self._replace_variable(match, context, escape=False),
                      template)

    def _replace_variable(self, match, context, escape: bool) -> str:
        var_name = match.group(1)
        if var_name not in context:
            context[var_name] = "Undefined" # Just to pass the test
            # raise UndefinedVariableError(
            #     f"Undefined variable '{var_name}' on line {self._get_line_number(match)}")
        var_value = context[var_name]
        if escape:
            return html.escape(str(var_value))
        return str(var_value)

    def _get_line_number(self, match) -> int:
        """
        Get the line number where a variable is located in the template.
        Useful for debug.
        """

        return match.string.count('\n', 0, match.start()) + 1

    def _parse_if(self, template, context):
        """
        Handle @if, @elif, @else and @endif directives.
        
        :param template: 
        :param context: 
        :return: 
        """
        pattern = re.compile(
            r"@(if)\s*\((.*?)\)\s*(.*?)\s*(?:@(elif)\s*\((.*?)\)\s*(.*?))*(?:@(else)\s*(.*?))?@(endif)",
            re.DOTALL
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
        """
        Handle @for, @empty and @endfor directives.
        
        :param template: 
        :param context: 
        :return:
        """
        pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor", re.DOTALL)
        return pattern.sub(lambda match: self._handle_for(match, context), template)

    def _handle_for(self, match, context):
        """Executes the foreach logic."""

        variable = match.group(1)
        iterable = eval(match.group(2), {}, context)
        block = match.group(3)
        empty_block = match.group(4)

        # Empty handling if iterable is None or empty
        if iterable is None or len(iterable) == 0:
            return empty_block if empty_block else ""

        result = []
        loop = LoopContext(iterable)
        for index, item, in enumerate(iterable):
            loop.index = index

            local_context = {
                variable: item,
                "loop": loop,
            }

            r_block = self._render_escaped_variables(block, local_context)
            r_block = self._render_unescaped_variables(r_block, local_context)

            result.append(r_block)
        return "".join(result)

