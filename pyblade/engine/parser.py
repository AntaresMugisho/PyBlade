import html
import re

from .contexts import LoopContext
from .exceptions import UndefinedVariableError
from .loader import load_template


class Parser:

    def __init__(self):
        self.directives = {
            "for": self._parse_for,
            "if": self._parse_if,
            "extends": self._parse_extends,
            "include": self._parse_include,
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

            # Reparse block for possible nested directives consideration
            parsed_block = self.parse(block, local_context)

            result.append(parsed_block)
        return "".join(result)

    def _parse_include(self, template, context):
        """Find partials code to include in the template"""

        pattern = re.compile(r"@include\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
        match = re.search(pattern, template)

        if match is not None:
            file_name = match.group(1) if match else None
            partial_template = load_template(file_name) if file_name else None

            if partial_template:
                # Parse the content to include before replacement
                partial_template = self.parse(partial_template, context)
                return re.sub(pattern, partial_template, template)

        return template

    def _parse_extends(self, template, context):
        """Search for extends directive in the template then parse sections inside."""

        pattern = re.compile(r"(.*?)@extends\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
        match = re.match(pattern, template)

        if match is not None:
            if match.group(1):
                raise Exception("The @extend tag must be at the top of the file before any character.")

            layout_name = match.group(2) if match else None
            if not layout_name:
                raise Exception("Layout not found")

            try:
                layout = load_template(f"layouts.{layout_name}")
                return self._parse_section(template, layout)
            except Exception as e:
                raise e

        return template

    def _parse_section(self, template, layout):
        """
        Find every section that can be yielded in the layout

        :param template: The partial template content
        :param layout: The layout content in which sections will be yielded
        :return: The full page after yield
        """

        pattern = re.compile(r"@section\s*\((?P<section_name>[^)]*)\)\s*(?P<content>.*?)@endsection", re.DOTALL)
        matches = pattern.findall(template)

        local_context = {}
        for match in matches:
            argument, content = match
            line_match_pattern = re.compile(rf"@section\s*\(({argument})\)", re.DOTALL)
            section_name = self._validate_argument(line_match_pattern.search(template))

            local_context[section_name] = content
            # TODO: Add a slot variable that will contain all the content outside the @section directives

        return self._parse_yield(layout, local_context)

    def _parse_yield(self, layout, context):
        """
        Replace every yieldable content by the actual value or None

        :param layout:
        :param context:
        :return:
        """
        pattern = re.compile(r"@yield\s*\(\s*(?P<yieldable_name>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_yield(match, context), layout)

    def _handle_yield(self, match, context):
        yieldable_name = self._validate_argument(match)
        return context.get(yieldable_name)

    def _validate_argument(self, match):
        argument = match.group(1)
        if (argument[0], argument[-1]) not in (('"', '"'), ("'", "'")) or len(argument.split(" ")) > 1:
            raise Exception(
                f"{argument} is not a valid string. Argument must be of type string."
                f"Look at line {self._get_line_number(match)}"
            )
        return argument[1:-1]
