import re
import html
from .exceptions import UndefinedVariableError


class LoopContext:
    """Holds context information for loops."""

    def __init__(self, items):
        self._total_items = len(items)
        self._current_index = 0

    @property
    def index(self):
        return self._current_index

    @index.setter
    def index(self, value):
        self._current_index = value

    @property
    def iteration(self):
        return self._current_index + 1

    @property
    def remaining(self):
        return self._total_items - self.iteration

    @property
    def count(self):
        return self._total_items

    @property
    def first(self):
        return self.index == 0

    @property
    def last(self):
        return self.iteration == self.count

    @property
    def even(self):
        return self.iteration % 2 == 0

    @property
    def odd(self):
        return self.iteration % 2 != 0

    def _depth(self):
        """Should return the nesting level of the current loop."""
        pass

    def _parent(self):
        """Should return the parent's loop variable, when in a nested loop."""
        pass


class Parser:

    def __init__(self):
        self.directives = {
            "if": self._parse_if,
            "for": self._parse_for
            # "empty": self._parse_empty
        }

    def parse_directives(self, template: str, context: dict):
        """
        Process all directives within a template.
        
        :param template: 
        :param context: 
        :return: 
        """
        
        template = self._parse_if(template, context)
        template = self._parse_for(template, context)
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
            raise UndefinedVariableError(
                f"Undefined variable '{var_name}' on line {self._get_line_number(match)}")
        var_value = context[var_name]
        if escape:
            return html.escape(str(var_value))
        return str(var_value)

    def _get_line_number(self, match):
        """Get the line number where a variable is located in the template"""

        return match.string.count('\n', 0, match.start()) + 1

    def _parse_if(self, template, context):
        """
        Handle, @if, @elif, @else and @endif directives.
        
        :param template: 
        :param context: 
        :return: 
        """
        pattern = re.compile(r"@if\s*\((.*?)\)\s*(.*?)@endif", re.DOTALL)
        return pattern.sub(lambda match: eval(match.group(1), {}, context) and match.group(2) or '', template)

    def _parse_for(self, template, context):
        """
        Handle @for, @empty and @endfor directives.
        
        :param template: 
        :param context: 
        :return:
        """
        pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(@empty\s*(.*?))?@endfor", re.DOTALL)
        return pattern.sub(lambda match: self._handle_for(match, context), template)

    def _handle_for(self, match, context):
        """Executes the foreach logic."""

        variable = match.group(1)
        iterable = eval(match.group(2), {}, context)
        block = match.group(3)
        # empty_directive = match.group(4)
        empty_block = match.group(5)

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
        return ''.join(result)
