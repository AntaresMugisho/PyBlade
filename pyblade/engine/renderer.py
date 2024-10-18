import re
import html

from .directives import PyBladeDirectives
from .exceptions import UndefinedVariableError


class PyBlade:
    def __init__(self):
        self.parser = PyBladeDirectives()
        self.directives = self.parser.directives

    def render(self, template: str, context: dict) -> str:
        template = self._load_template(template)

        template = self._process_directives(template, context)
        template = self._render_unescaped_variables(template, context)
        template = self._render_escaped_variables(template, context)
        return template

    def _load_template(self, template_name: str):
        """Loads the template file"""

        with open(template_name, "r") as file:
            return file.read()

    def _process_directives(self, template: str, context: dict) -> str:
        """Applies all registered directives in the template."""

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
            raise UndefinedVariableError(
                f"Undefined variable '{var_name}' on line {self._get_line_number(match)}")
        var_value = context[var_name]
        if escape:
            return html.escape(str(var_value))
        return str(var_value)

    def _get_line_number(self, match):
        """Get the line number where a variable is located in the template"""

        return match.string.count('\n', 0, match.start()) + 1
