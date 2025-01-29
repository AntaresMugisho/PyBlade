"""
Directive parsing implementation for the template engine.
"""

import ast
import html
import importlib
import json
import keyword
import re
from datetime import datetime
from pprint import pformat, pprint  # noqa
from typing import Any, Dict, Match, Pattern, Tuple
from uuid import uuid4

from pyblade.engine import loader

from ..contexts import (
    AttributesContext,
    CycleContext,
    ErrorMessageContext,
    LoopContext,
    SlotContext,
)
from ..exceptions import (
    DirectiveParsingError,
    TemplateRenderingError,
    UndefinedVariableError,
)
from .variables import VariableParser


class DirectiveParser:
    """Handles parsing and processing of template directives."""

    # Cached regex patterns
    _ESCAPED_VAR_PATTERN: Pattern = re.compile(r"{{\s*(.*?)\s*}}")
    _FOR_PATTERN: Pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor", re.DOTALL)
    _IF_PATTERN: Pattern = re.compile(
        r"@(if)\s*\((.*?\)?)\)\s*(.*?)\s*(?:@(elif)\s*\((.*?\)?)\)\s*(.*?))*(?:@(else)\s*(.*?))?@(endif)", re.DOTALL
    )
    _UNLESS_PATTERN: Pattern = re.compile(r"@unless\s*\((?P<expression>.*?)\)(?P<slot>.*?)@endunless", re.DOTALL)
    _SWITCH_PATTERN: Pattern = re.compile(
        r"@(?P<directive>switch|match)\s*\((?P<expression>.*?)\)\s*(?P<cases>.*?)@end(?P=directive)", re.DOTALL
    )
    _CASE_PATTERN: Pattern = re.compile(
        r"@case\s*\((?P<value>.*?)\)\s*(?P<content>.*?)(?=@case|@default|@end(switch|match)|$)", re.DOTALL
    )
    _DEFAULT_PATTERN: Pattern = re.compile(r"@default\s*(?P<content>.*?)$", re.DOTALL)
    _COMMENTS_PATTERN: Pattern = re.compile(r"{#(.*?)#}", re.DOTALL)

    # New Django-like directive patterns
    _AUTOESCAPE_PATTERN: Pattern = re.compile(
        r"@autoescape\s*\((?P<mode>True|False|on|off)\)\s*(?P<content>.*?)@endautoescape", re.DOTALL
    )
    _CYCLE_PATTERN: Pattern = re.compile(
        r"@cycle\s*\((?P<values>.*?)(?:(?P<alias>\s*as\s*)(?P<variable>\w+))?\)", re.DOTALL
    )
    _DEBUG_PATTERN: Pattern = re.compile(r"@debug", re.DOTALL)

    _EXTENDS_PATTERN: Pattern = re.compile(r"(.*?)@extends\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
    _SECTION_PATTERN: Pattern = re.compile(
        r"@(?P<directive>section|block)\s*\((?P<section_name>[^)]*)\)\s*(?P<content>.*?)@end(?P=directive)", re.DOTALL
    )
    _FILTER_PATTERN: Pattern = re.compile(r"@filter\s*\((?P<filters>.*?)\)\s*(?P<content>.*?)@endfilter", re.DOTALL)
    _FIRSTOF_PATTERN: Pattern = re.compile(
        r"@firstof\s*\((?P<values>.*?)(?:\s*,\s*default=(?P<default>.*?))?\)", re.DOTALL
    )
    _IFCHANGED_PATTERN: Pattern = re.compile(
        r"@ifchanged\s*(?:\((?P<expressions>.*?)\))?\s*(?P<content>.*?)(?:@else\s*(?P<else_content>.*?))?@endifchanged",
        re.DOTALL,
    )
    _LOREM_PATTERN: Pattern = re.compile(
        r"@lorem\s*\((?P<count>\d+)?(?:\s*,\s*(?P<method>w|p|b))?(?:\s*,\s*(?P<random>random))?\)", re.DOTALL
    )
    _NOW_PATTERN: Pattern = re.compile(
        r"@now\s*\((?P<format>.*?)(?:(?P<alias>\s*as\s*)(?P<variable>\w+))?\)", re.DOTALL
    )
    _QUERYSTRING_PATTERN: Pattern = re.compile(r"@querystring(?:\s*\((?P<updates>.*?)\))?", re.DOTALL)
    _REGROUP_PATTERN: Pattern = re.compile(
        r"@regroup\s*\((?P<expression>.*?)\s+by\s+(?P<grouper>.*?)\s+as\s+(?P<var_name>.*?)\)", re.DOTALL
    )
    _SPACELESS_PATTERN: Pattern = re.compile(r"@spaceless\s*(?P<content>.*?)@endspaceless", re.DOTALL)
    _STYLE_PATTERN: Pattern = re.compile(r"@style\s*\((?P<styles>.*?)\)", re.DOTALL)
    _CLASS_PATTERN: Pattern = re.compile(r"@class\s*\((?P<classes>.*?)\)", re.DOTALL)
    _TEMPLATETAG_PATTERN: Pattern = re.compile(r"@templatetag\s*\((?P<tag>.*?)\)", re.DOTALL)
    _WIDTHRATIO_PATTERN: Pattern = re.compile(
        r"@widthratio\s*\((?P<value>.*?)\s*,\s*(?P<max_value>.*?)\s*,\s*(?P<max_width>.*?)\)", re.DOTALL
    )
    _WITH_PATTERN: Pattern = re.compile(
        r"@with\s*\((?P<expression>.*?)\s*as\s*(?P<variable>.*?)\)\s*(?P<content>.*?)\s*@endwith", re.DOTALL
    )
    _COMMENT_PATTERN: Pattern = re.compile(r"@comment\s*(?P<content>.*?)@endcomment", re.DOTALL)
    _VERBATIM_PATTERN: Pattern = re.compile(r"@verbatim\s*(?P<content>.*?)@endverbatim", re.DOTALL)
    _VERBATIM_SHORTHAND_PATTERN: Pattern = re.compile(r"@(?P<content>{{.*?}})", re.DOTALL)
    _VERBATIM_PLACEHOLDER_PATTERN: Pattern = re.compile(r"@__verbatim__\((?P<id>\w+)\)", re.DOTALL)
    _CSRF_PATTERN: Pattern = re.compile(r"@csrf", re.DOTALL)
    _METHOD_PATTERN: Pattern = re.compile(r"@method\s*\(\s*(?P<method>.*?)\s*\)", re.DOTALL)
    _CONDITIONAL_ATTRIBUTES_PATTERN: Pattern = re.compile(
        r"@(?P<directive>checked|selected|required|disabled|readonly|multiple|autofocus|autocomplete)\s*(?:\(\s*(?P<expression>.*?)\s*\))?",  # noqa
        re.DOTALL,
    )
    _COMPONENT_PATTERN: Pattern = re.compile(
        r"@component\s*\(\s*(?P<name>.*?)\s*(?:,\s*(?P<data>.*?))?\s*\)(?P<slot>.*?)", re.DOTALL
    )
    _SLOT_PATTERN: Pattern = re.compile(r"@slot\s*\((?P<name>.*?)\)(?P<content>\s*.*?\s*)@endslot", re.DOTALL)
    _SLOT_SHORTHAND_PATTERN: Pattern = re.compile(r"@slot\((?P<name>.*?)\s*,\s*(?P<content>.*?)\)", re.DOTALL)
    _SLOT_TAG_PATTERN: Pattern = re.compile(
        r"<b-slot(?::|\s+name\s*=\s*)(?P<name>.*?)>\s*(?P<content>.*?)\s*</b-slot(?::(?P=name))?>", re.DOTALL
    )
    _LIVEBLADE_PATTERN = re.compile(r"@liveblade\s*\(\s*(?P<component>.*?)\s*\)", re.DOTALL)
    _LIVEBLADE_SCRIPTS_PATTERN: Pattern = re.compile(
        r"@(?:liveblade_scripts|livebladeScripts)(?:\s*\(\s*(?P<attributes>.*?)\s*\))?", re.DOTALL
    )
    _INCLUDE_PATTERN: Pattern = re.compile(r"@include\s*\(\s*(?P<path>.*?)\s*\)", re.DOTALL)
    _FIELD_PATTERN: Pattern = re.compile(
        r"@field\s*\((?P<field>.*?)\s*(?:,\s*(?P<attributes>.*?\)?\s*\}?\}?))?\)", re.DOTALL
    )
    _ERROR_PATTERN: Pattern = re.compile(r"@error\s*\((?P<field>.*?)\s*\)\s*(?P<slot>.*?)\s*@enderror", re.DOTALL)
    _OPENING_TAG_PATTERN: Pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>")

    # Bootstrap directive patterns
    _BOOTSTRAP_CSS_PATTERN: Pattern = re.compile(r"@bootstrap_css", re.DOTALL)
    _BOOTSTRAP_JS_PATTERN: Pattern = re.compile(r"@bootstrap_javascript", re.DOTALL)

    # Tailwind directive patterns
    _TAILWIND_CSS_PATTERN: Pattern = re.compile(r"@tailwind_css", re.DOTALL)
    _TAILWIND_PRELOAD_CSS_PATTERN: Pattern = re.compile(r"@tailwind_preload_css", re.DOTALL)

    def __init__(self):
        self._context: Dict[str, Any] = {}
        self._line_map: Dict[str, int] = {}  # Maps directive positions to line numbers
        self._variable_parser = VariableParser()
        self.verbatims = {}
        self.initial_template = ""

    def _get_line_number(self, match: Match) -> int:
        """Get the line number for a position in the template."""
        return self.initial_template.count("\n", 0, match.start()) + 1

    def _check_unclosed_tags(self, template: str) -> None:
        """Check for unclosed directive tags and report their line numbers."""
        # Define pairs of opening and closing tags
        tag_pairs = {"@if": "@endif", "@for": "@endfor", "@unless": "@endunless", "@switch": "@endswitch"}

        for start_tag, end_tag in tag_pairs.items():
            # Find all occurrences of start tags
            start_positions = [m.start() for m in re.finditer(re.escape(start_tag), template)]
            end_positions = [m.start() for m in re.finditer(re.escape(end_tag), template)]

            if len(start_positions) > len(end_positions):
                # Find the first unclosed tag
                for pos in start_positions:
                    # Count matching end tags before this position
                    matching_ends = sum(1 for end_pos in end_positions if end_pos > pos)
                    if matching_ends < 1:
                        line_number = 0  # TODO: use regex match
                        raise DirectiveParsingError(f"Unclosed {start_tag} directive at line {line_number}")

    def parse_directives(self, template: str, context: Dict[str, Any]) -> str:
        """
        Process all directives within a template.

        Args:
            template: The template string
            context: The context dictionary

        Returns:
            The processed template
        """
        self._context = context
        self._check_unclosed_tags(template)

        # Process slots first to ensure they're captured before component rendering
        # template = self._process_slots(template, context)

        # Process directives in order
        template = self._parse_comments(template)
        template = self._parse_verbatim_shorthand(template)
        template = self._parse_verbatim(template)
        template = self._parse_for(template)
        template = self._parse_if(template)
        template = self._parse_switch(template)
        template = self._parse_unless(template)
        template = self._parse_auth(template)
        template = self._parse_guest(template)
        template = self._parse_anonymous(template)
        template = self._parse_class(template)
        template = self._parse_style(template)
        template = self._parse_active(template)

        # Form helpers
        template = self._parse_csrf(template)
        template = self._parse_method(template)
        template = self._parse_conditional_attributes(template)
        template = self._parse_field(template)
        template = self._parse_error(template)

        # Components related
        # Parse slots first to ensure they're captured before any component rendering
        template = self._parse_slot_tags(template)
        template = self._parse_pyblade_tags(template)
        template = self._parse_component(template)
        template = self._parse_include(template)
        template = self._parse_extends(template)

        # Django-like directives
        template = self._parse_static(template)
        template = self._parse_now(template)
        template = self._parse_cycle(template)
        template = self._parse_debug(template)
        template = self._parse_filter(template)
        template = self._parse_firstof(template)
        template = self._parse_ifchanged(template)
        template = self._parse_lorem(template)
        template = self._parse_querystring(template)
        template = self._parse_regroup(template)
        template = self._parse_spaceless(template)
        template = self._parse_templatetag(template)
        template = self._parse_widthratio(template)
        template = self._parse_with(template)
        template = self._parse_component(template)
        template = self._parse_url(template)
        template = self._parse_autoescape(template)

        # Process liveblade
        template = self._parse_liveblade_scripts(template)
        template = self._parse_liveblade(template)

        # Process Bootstrap directives
        template = self._process_bootstrap_css(template, context)
        template = self._process_bootstrap_javascript(template, context)

        # Process Tailwind directives
        template = self._process_tailwind_preload_css(template, context)
        template = self._process_tailwind_css(template, context)

        # Restore verbatim content
        template = self._restore_verbatim(template)

        return template

    def _parse_for(self, template: str) -> str:
        """Process @for loops with @empty fallback."""
        return self._FOR_PATTERN.sub(self._handle_for, template)

    def _handle_for(self, match: Match) -> str:
        """Handle @for loop logic with proper error handling."""
        try:
            variable = self._validate_variable_name(match.group(1).strip())
            iterable_expression = match.group(2).strip()
            block = match.group(3)
            empty_block = match.group(4)

            try:
                iterable = eval(iterable_expression, {}, self._context)
            except Exception as e:
                raise DirectiveParsingError(f"Error evaluating iterable expression '{iterable_expression}': {str(e)}")

            if not iterable:
                return empty_block if empty_block else ""

            result = []
            current_loop = self._context.get("loop")
            loop = LoopContext(iterable, parent=current_loop)

            for index, item in enumerate(iterable):
                loop.index = index

                self._context.update({variable: item, "loop": loop})

                parsed_block = self.parse_directives(block, self._context)
                parsed_block = self._variable_parser.parse_variables(block, self._context)

                should_break, parsed_block = self._parse_break(parsed_block, self._context)
                should_continue, parsed_block = self._parse_continue(parsed_block, self._context)

                if should_break:
                    break
                if should_continue:
                    continue

                result.append(parsed_block)

            self._context.pop("loop")
            return "".join(result)

        except Exception as e:
            raise DirectiveParsingError(f"Error in @for directive: {str(e)}")

    def _parse_if(self, template: str) -> str:
        """Process @if, @elif, and @else directives."""

        def replace_if(match: Match) -> str:
            try:
                captures = [group for group in match.groups()]

                for i, capture in enumerate(captures[:-1]):
                    if capture in ("if", "elif", "else"):
                        if capture in ("if", "elif"):
                            if eval(captures[i + 1], {}, self._context):
                                return captures[i + 2]
                        else:
                            return captures[i + 1]

            except Exception as e:
                raise DirectiveParsingError(f"Error in @if directive: {str(e)}")

        return self._IF_PATTERN.sub(replace_if, template)

    def _parse_unless(self, template: str) -> str:
        """Process @unless directives."""

        def replace_unless(match: Match) -> str:
            try:
                expression = match.group("expression")
                slot = match.group("slot")

                try:
                    condition = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(f"Error evaluating unless condition '{expression}': {str(e)}")

                return "" if condition else slot

            except Exception as e:
                raise DirectiveParsingError(f"Error in @unless directive: {str(e)}")

        return self._UNLESS_PATTERN.sub(replace_unless, template)

    def _parse_switch(self, template: str) -> str:
        """Process @switch, @case, and @default directives."""

        def replace_switch(match: Match) -> str:
            try:
                expression = match.group("expression")
                cases_block = match.group("cases")

                # Evaluate the switch expression
                try:
                    switch_value = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(f"Error evaluating switch expression '{expression}': {str(e)}")

                # Find all cases
                cases = self._CASE_PATTERN.finditer(cases_block)
                default_match = self._DEFAULT_PATTERN.search(cases_block)

                # Check each case
                for case in cases:
                    case_value = case.group("value")
                    try:
                        case_result = eval(case_value, {}, self._context)
                    except Exception as e:
                        raise DirectiveParsingError(f"Error evaluating case value '{case_value}': {str(e)}")

                    if case_result == switch_value:
                        return self.parse_directives(case.group("content"), self._context)

                # If no case matched and there's a default, use it
                if default_match:
                    return self.parse_directives(default_match.group("content"), self._context)

                return ""

            except Exception as e:
                raise DirectiveParsingError(f"Error in @switch directive: {str(e)}")

        return self._SWITCH_PATTERN.sub(replace_switch, template)

    def _parse_comments(self, template: str) -> str:
        """Process both inline comments ({# #}) and block comments (@comment)."""
        # First process inline comments
        template = self._COMMENTS_PATTERN.sub("", template)

        # Then process block comments
        def replace_comment(match: Match) -> str:
            try:
                return ""  # Remove the comment and its content
            except Exception as e:
                raise DirectiveParsingError(f"Error in comment directive: {str(e)}")

        return self._COMMENT_PATTERN.sub(replace_comment, template)

    def _parse_verbatim(self, template: str) -> str:
        """
        Process both @verbatim blocks and shorthand verbatim (@{{ }}).
        The shorthand is processed first to prevent interference with block processing.
        """

        def replace_verbatim(match: Match) -> str:
            try:
                verbatim_content = match.group("content")

                verbatim_id = uuid4().hex
                self._context.setdefault("__verbatims", {})[verbatim_id] = verbatim_content
                return f"@__verbatim__({verbatim_id})"

            except Exception as e:
                raise DirectiveParsingError(f"Error in @verbatim directive: {str(e)}")

        template = self._VERBATIM_SHORTHAND_PATTERN.sub(replace_verbatim, template)

        return self._VERBATIM_PATTERN.sub(replace_verbatim, template)

    def _restore_verbatim(self, template: str) -> str:
        """
        Process all @__verbatim__(<id>) placeholders in the template and replace them
        with the corresponding verbatim content.
        This function is called to restore the verbatim content after processing.
        """

        def replace_verbatim_placeholder(match):
            verbatims = self._context.get("__verbatims", {})
            return verbatims.pop(match.group("id"))

        return self._VERBATIM_PLACEHOLDER_PATTERN.sub(replace_verbatim_placeholder, template)

    def _parse_url(self, template: str) -> str:
        """Process @url directive with support for Django-style 'as' variable assignment."""

        def replace_url(match: Match) -> str:
            url_pattern = match.group("pattern").strip("'\"")
            params = match.group("params")
            as_var = match.group("as_var")

            # Build URL parameters
            url_params = []
            if params:
                for param in params.split(","):
                    param = param.strip()
                    if "=" in param:
                        key, value = param.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        try:
                            # Evaluate the value in the current context
                            evaluated_value = eval(value, {}, self._context)
                            url_params.append((key, evaluated_value))
                        except Exception as e:
                            raise DirectiveParsingError(f"Error evaluating URL parameter '{value}': {str(e)}")

            # Get URL patterns from context
            urlconf = self._context.get("urlconf", None)
            if not urlconf:
                raise DirectiveParsingError("URL configuration not found in context")

            try:
                # Resolve URL pattern
                from django.urls import reverse

                url = reverse(
                    url_pattern,
                    args=[p[1] for p in url_params if not p[0]],
                    kwargs={p[0]: p[1] for p in url_params if p[0]},
                )

                # If 'as' variable is specified, store in context and return empty string
                if as_var:
                    self._context[as_var.strip()] = url
                    return ""
                return url

            except Exception as e:
                raise DirectiveParsingError(f"Error resolving URL '{url_pattern}': {str(e)}")

        # Updated pattern to support 'as' variable assignment
        url_pattern = re.compile(
            r"@url\s*\(\s*(?P<pattern>['\"].*?['\"])\s*(?:,\s*(?P<params>.*?))?\s*(?:\s+as\s+(?P<as_var>\w+))?\s*\)",
            re.DOTALL,
        )

        return url_pattern.sub(replace_url, template)

    def _parse_break(self, template: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Process @break directives."""
        pattern = re.compile(r"@break(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @break directive: {str(e)}")
        return False, template

    def _parse_continue(self, template: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Process @continue directives."""
        pattern = re.compile(r"@continue(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @continue directive: {str(e)}")
        return False, template

    def _parse_auth_or_guest(self, template):
        """
        Generalized method to parse @auth or @guest directives.
        """

        def handle_auth_or_guest(match):
            """
            Generalized handler for @auth and @guest directives.
            """
            directive = match.group("directive")

            is_authenticated = False
            request = self._context.get("request", None)
            if request:
                try:
                    is_authenticated = request.user.is_authenticated
                except Exception as e:
                    raise Exception(str(e))

            should_render_first_block = is_authenticated if directive == "auth" else not is_authenticated

            captures = [group for group in match.groups() if group not in (None, "")]
            for i, capture in enumerate(captures[:-1]):
                if capture == directive:
                    if should_render_first_block:
                        return captures[i + 1]
                elif capture == "else":
                    if not should_render_first_block:
                        return captures[i + 1]

        pattern = re.compile(
            r"@(?P<directive>auth|guest|anonymous)\s*(.*?)\s*(?:@(else)\s*(.*?))?\s*@end(?P=directive)", re.DOTALL
        )
        return pattern.sub(lambda match: handle_auth_or_guest(match), template)

    def _parse_auth(self, template):
        """Check if the user is authenticated."""
        return self._parse_auth_or_guest(template)

    def _parse_guest(self, template):
        """Check if the user is not authenticated."""
        return self._parse_auth_or_guest(template)

    def _parse_anonymous(self, template):
        """Check if the user is not authenticated. Same as @guest"""
        return self._parse_auth_or_guest(template)

    def _parse_include(self, template: str) -> str:
        """
        Process @include directives to include partial templates.

        Example:
            @include("partials.header")

        The path is dot-separated and will be converted to a file path:
        - "partials.header" -> "partials/header.html"
        - "components.navbar" -> "components/navbar.html"

        Args:
            template: The template string

        Returns:
            The processed template with included partials
        """

        def replace_include(match: Match) -> str:
            try:
                # Get the dot-separated path and optional data
                path = self._validate_string(match.group("path"))

                try:
                    partial_template = loader.load_template(path)
                    return self.parse_directives(partial_template.content, self._context)
                except Exception as e:
                    raise DirectiveParsingError(f"Error loading partial template {path}: {str(e)}")

            except Exception as e:
                raise DirectiveParsingError(f"Error in @include directive: {str(e)}")

        return self._INCLUDE_PATTERN.sub(replace_include, template)

    def _parse_extends(self, template):
        """Search for extends directive in the template then parse sections inside."""

        # Find all @extends directives in the template
        extends_matches = list(self._EXTENDS_PATTERN.finditer(template))

        # Check for multiple @extends directives
        if len(extends_matches) > 1:
            raise DirectiveParsingError(
                "Multiple @extends directives found. Only one @extends directive is allowed per template."
            )

        # Get the first (and should be only) match
        match = extends_matches[0] if extends_matches else None
        template = re.sub(self._EXTENDS_PATTERN, "", template)

        if match:
            if match.group(1):
                raise DirectiveParsingError("The @extends tag must be at the top of the file before any character.")

            layout_name = match.group(2) if match else None
            if not layout_name:
                raise DirectiveParsingError("Missing layout name in @extends directive")

            try:
                # The following line order is important
                layout = loader.load_template(layout_name)
                sections = self._parse_section(template)
                parsed_layout = layout.render(self._context)
                template = self._parse_yield(parsed_layout, sections)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @extends directive: {str(e)}")

        return template

    def _parse_section(self, template):
        """
        Find every section that can be yielded in the layout.
        Sections may be inside @section(<name>) and @endsection directives, or inside
        @block(<name>) and @endblock directives.

        :param template: The partial template content
        :param layout: The layout content in which sections will be yielded
        :return: The full page after yield
        """

        def handle_section(match: Match) -> str:
            try:
                section_name = ast.literal_eval(match.group("section_name"))
                section_content = match.group("content")
            except Exception as e:
                raise DirectiveParsingError(f"Error in @section directive: {str(e)}")

            sections[section_name] = section_content
            return ""

        sections = {}
        template = re.sub(self._SECTION_PATTERN, handle_section, template)

        self._context["slot"] = SlotContext(template.strip())

        return sections

    def _parse_yield(self, layout, sections: Dict[str, str]):
        """
        Replace every yieldable content by the actual value or None

        :param layout:
        :return:
        """
        pattern = re.compile(r"@yield\s*\(\s*(?P<yieldable_name>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_yield(match, sections), layout)

    def _handle_yield(self, match, sections: Dict[str, str] = None):
        yieldable_name = self._validate_variable_name(match.group("yieldable_name"))
        return sections.get(yieldable_name)

    def _parse_slot_tags(self, template):
        """Inject slot content into the context."""

        def handle_slot_tags(match, shorthand=False):
            name = self._validate_variable_name(match.group("name"))
            content = match.group("content")
            if shorthand:
                content = self._validate_string(content)
            self._context[name] = SlotContext(content)
            return ""

        template = self._SLOT_SHORTHAND_PATTERN.sub(lambda match: handle_slot_tags(match, True), template)
        # Disable long-hand slot tags cause of conflicts with short-hand
        # template = re.sub(self._SLOT_PATTERN, handle_slot_tags, template)
        template = self._SLOT_TAG_PATTERN.sub(handle_slot_tags, template)

        return template

    def _parse_pyblade_tags(self, template):
        pattern = re.compile(
            r"<b-(?P<component>\w+-?\w+)\s*(?P<attributes>.*?)\s*(?:/>|>(?P<slot>.*?)</b-(?P=component)>)", re.DOTALL
        )
        return pattern.sub(lambda match: self._handle_pyblade_tags(match), template)

    def _handle_pyblade_tags(self, match):
        component_name = match.group("component")
        component = loader.load_template(f"components.{component_name}")

        attr_string = match.group("attributes")
        attr_pattern = re.compile(r"(?P<attribute>:?\w+)(?:\s*=\s*(?P<value>[\"']?.*?[\"']))?", re.DOTALL)
        attrs = attr_pattern.findall(attr_string)

        attributes = {}
        component_context = {}

        for attr in attrs:
            name, value = attr
            value = value[1:-1]
            if name.startswith(":"):
                name = name[1:]
                try:
                    value = eval(value, {}, self._context) if value else None
                except NameError as e:
                    raise e

                component_context[name] = value

            attributes[name] = value

        component_context.update(attributes)

        new_content, props = self._parse_props(component.content)
        component.content = new_content

        attributes = AttributesContext(props, attributes, component_context)
        component_context["attributes"] = attributes
        component_context["slot"] = SlotContext(match.group("slot"))

        parsed_component = component.render(component_context)
        return parsed_component

    def _parse_props(self, component: str) -> tuple:
        pattern = re.compile(r"@props\s*\((?P<dictionary>.*?)\s*\)", re.DOTALL)
        match = pattern.search(component)

        props = {}
        if match:
            component = re.sub(pattern, "", component)
            dictionary = match.group("dictionary")
            try:
                props = eval(dictionary, {}, self._context)
            except SyntaxError as e:
                raise e
            except ValueError as e:
                raise e

        return component, props

    def _parse_component(self, template: str) -> str:
        """Process @component directive for reusable template components."""

        def replace_component(match: Match) -> str:
            try:
                component_name = self._validate_string(match.group("name"))
                data = match.group("data")

                component = loader.load_template(f"components.{component_name}")

                component_context = {}
                if data:
                    try:
                        component_context = eval(data, {}, self._context)
                    except Exception as e:
                        raise DirectiveParsingError(f"Error processing component data: {str(e)}")

                new_content, props = self._parse_props(component.content)
                attributes = AttributesContext(props, {}, component_context)
                component_context["attributes"] = attributes

                component.content = new_content
                return component.render(component_context)

            except Exception as e:
                raise DirectiveParsingError(f"Error in @component directive: {str(e)}")

        return self._COMPONENT_PATTERN.sub(replace_component, template)

    def _parse_class(self, template: str) -> str:
        """
        Process @class directives to conditionally apply HTML classes.

        Example:
            @class({'active': isActive, 'disabled': isDisabled})

        Args:
            template: The template string

        Returns:
            The processed template with class attributes
        """

        def replace_class(match: Match) -> str:
            try:
                # Get the classes dictionary from the directive
                classes_str = match.group("classes").strip()

                # Evaluate the dictionary using eval for consistency with style directive
                classes_dict = eval(classes_str, {}, self._context)

                if not isinstance(classes_dict, dict):
                    raise DirectiveParsingError("@class directive requires a dictionary")

                active_classes = []
                for class_name, condition in classes_dict.items():
                    # Evaluate the condition if it's not already a boolean
                    if not isinstance(condition, bool):
                        condition = eval(str(condition), {}, self._context)

                    if condition:
                        # Clean up class name, removing quotes and extra spaces
                        clean_class = class_name.strip().strip("\"'")
                        if clean_class:
                            active_classes.append(clean_class)

                # If we have active classes, return them as a class attribute
                if active_classes:
                    return f' class="{" ".join(active_classes)}"'
                return ""

            except Exception as e:
                raise DirectiveParsingError(f"Error in @class directive: {str(e)}")

        return self._CLASS_PATTERN.sub(replace_class, template)

    def _parse_style(self, template: str) -> str:
        """
        Process @style directives to conditionally apply inline styles.

        Example:
            @style({'color: red;': isError, 'font-weight: bold;': isBold})

        Args:
            template: The template string

        Returns:
            The processed template with style attributes
        """

        def replace_style(match: Match) -> str:
            try:
                # Get the styles dictionary from the directive
                styles_str = match.group("styles").strip()

                styles_dict = eval(styles_str, {}, self._context)

                if not isinstance(styles_dict, dict):
                    raise DirectiveParsingError("@style directive requires a dictionary")

                active_styles = []
                for style, condition in styles_dict.items():
                    if not isinstance(condition, bool):
                        condition = eval(str(condition), {}, self._context)

                    if condition:
                        # Remove any existing 'style="' or '"' from the style string
                        clean_style = style.strip().rstrip(";").strip("\"'")
                        if clean_style:
                            active_styles.append(clean_style)

                if active_styles:
                    return f' style="{"; ".join(active_styles)};"'
                return ""

            except Exception as e:
                raise DirectiveParsingError(f"Error in @style directive: {str(e)}")

        return self._STYLE_PATTERN.sub(replace_style, template)

    def _parse_autoescape(self, template: str) -> str:
        """Process @autoescape directive for controlling HTML escaping."""

        def replace_autoescape(match: Match) -> str:
            try:
                mode = match.group("mode")
                content = match.group("content")

                mode = True if str(mode) in ("on", "True") else False
                if not mode:
                    return re.sub(self._ESCAPED_VAR_PATTERN, r"{!! \1 !!}", content)

                return content

            except Exception as e:
                raise DirectiveParsingError(f"Error in @autoescape directive: {str(e)}")

        return self._AUTOESCAPE_PATTERN.sub(replace_autoescape, template)

    def _parse_cycle(self, template: str) -> str:
        """Process @cycle directive for cycling through a list of values."""

        def replace_cycle(match: Match) -> str:
            try:
                values_str = match.group("values")
                alias = match.group("alias") or None
                var_name = match.group("variable")

                if alias and str(alias) != " as ":
                    raise DirectiveParsingError("Syntax error in @cycle directive: alias must be ' as '")

                # Parse the values
                values = []
                for val in values_str.split(","):
                    val = val.strip().strip("'\"")
                    if val:
                        if val in self._context.keys():
                            values.append(f"{{{{ {val} }}}}")
                            continue
                        values.append(val)

                if not values:
                    raise DirectiveParsingError("Cycle values cannot be empty")

                # Initialize cycle tracking in context if not exists
                self._context.setdefault("__cycle_vars__", {})

                # If this is not a named cycle

                # Check if this is a reference to an existing cycle
                # if len(values) == 1:
                #     if isinstance(values[0], CycleContext):
                #         cycle: CycleContext = values[0]
                #         cycle.index += 1
                #         self._context[str(values_str)] = cycle.current
                #         return cycle.current

                cycle_key = var_name or values_str

                cycle = self._context.get("__cycle_vars__").get(cycle_key, CycleContext(values, values_str))
                current_value = cycle.current

                # If this is a named cycle, store the variable in the context
                if var_name:
                    self._context[var_name] = current_value

                # Store current value in context for direct access
                self._context["__cycle_vars__"].setdefault(cycle_key, cycle)
                cycle.index += 1
                return current_value

            except Exception as e:
                raise DirectiveParsingError(f"Error in @cycle directive: {str(e)}")

        content = self._CYCLE_PATTERN.sub(replace_cycle, template)
        return content

    def _parse_debug(self, template: str) -> str:
        """Process @debug directive to output debugging information."""

        def replace_debug(match: Match) -> str:
            try:
                debug_context = {k: v for k, v in sorted(self._context.items()) if not k.startswith("_")}
                pretty_debug_context = pformat(debug_context, indent=4, width=120, depth=4)
                return f"<pre>{html.escape(pretty_debug_context)}</pre>"
            except Exception as e:
                raise DirectiveParsingError(f"Error in @debug directive: {str(e)}")

        return self._DEBUG_PATTERN.sub(replace_debug, template)

    def _parse_filter(self, template: str) -> str:
        """Process @filter directive to apply filters to content."""

        return template
        # TODO: Add support for filters

        def replace_filter(match: Match) -> str:
            try:
                filters = match.group("filters").split("|")
                content = match.group("content")

                # Process content first
                result = self.parse_directives(content, self._context)

                # Apply each filter in sequence
                for filter_name in filters:
                    filter_name = filter_name.strip()
                    if hasattr(self, f"_filter_{filter_name}"):
                        filter_func = getattr(self, f"_filter_{filter_name}")
                        result = filter_func(result)
                    else:
                        raise DirectiveParsingError(f"Unknown filter: {filter_name}")

                return result
            except Exception as e:
                raise DirectiveParsingError(f"Error in @filter directive: {str(e)}")

        return self._FILTER_PATTERN.sub(replace_filter, template)

    def _parse_firstof(self, template: str) -> str:
        """Process @firstof directive to output the first non-empty value."""

        def replace_firstof(match: Match) -> str:
            try:
                values = [v.strip() for v in match.group("values").split(",")]
                default = match.group("default")

                for value in values:
                    try:
                        result = eval(value, {}, self._context)
                        if result:
                            return str(result)
                    except Exception:
                        continue

                return str(default) if default else ""
            except Exception as e:
                raise DirectiveParsingError(f"Error in @firstof directive: {str(e)}")

        return self._FIRSTOF_PATTERN.sub(replace_firstof, template)

    def _parse_ifchanged(self, template: str) -> str:
        """Process @ifchanged directive to conditionally output content if it has changed."""

        def replace_ifchanged(match: Match) -> str:
            try:
                expressions = match.group("expressions")
                content = match.group("content")
                else_content = match.group("else_content")

                # Initialize storage for last values if not present
                if "_ifchanged_last_values" not in self._context:
                    self._context["_ifchanged_last_values"] = {}

                # Generate a unique key for this ifchanged block
                key = f"ifchanged_{hash(content)}"

                if expressions:
                    # Watch for changes in specific variables
                    current_values = tuple(eval(expr.strip(), {}, self._context) for expr in expressions.split(","))
                else:
                    # Watch for changes in the rendered content
                    current_values = (self.parse_directives(content, self._context),)

                last_values = self._context["_ifchanged_last_values"].get(key)

                if last_values != current_values:
                    self._context["_ifchanged_last_values"][key] = current_values
                    return self.parse_directives(content, self._context)
                elif else_content:
                    return self.parse_directives(else_content, self._context)
                return ""

            except Exception as e:
                raise DirectiveParsingError(f"Error in @ifchanged directive: {str(e)}")

        return self._IFCHANGED_PATTERN.sub(replace_ifchanged, template)

    def _parse_lorem(self, template: str) -> str:
        """Process @lorem directive to generate Lorem Ipsum text."""
        import random

        WORDS = [
            "lorem",
            "ipsum",
            "dolor",
            "sit",
            "amet",
            "consectetur",
            "adipiscing",
            "elit",
            "sed",
            "do",
            "eiusmod",
            "tempor",
            "incididunt",
            "ut",
            "labore",
            "et",
            "dolore",
            "magna",
            "aliqua",
        ]

        def generate_words(count: int, random_order: bool = False) -> str:
            words = WORDS.copy()
            if random_order:
                random.shuffle(words)
            while len(words) < count:
                words.extend(WORDS)
            return " ".join(words[:count])

        def generate_paragraphs(count: int, random_order: bool = False) -> str:
            paragraphs = []
            for _ in range(count):
                words = generate_words(random.randint(20, 100), random_order)
                paragraphs.append(words.capitalize() + ".")
            return paragraphs

        def replace_lorem(match: Match) -> str:
            try:
                count = int(match.group("count"))
                method = match.group("method") or "w"
                random_order = bool(match.group("random"))

                if method == "w":
                    return generate_words(count, random_order)
                elif method == "b":
                    return "\n\n".join(generate_paragraphs(count, random_order))
                elif method == "p":
                    return "".join([f"<p>{p}</p>" for p in generate_paragraphs(count, random_order)])
                else:
                    raise DirectiveParsingError(f"Invalid lorem method: {method}")

            except Exception as e:
                raise DirectiveParsingError(f"Error in @lorem directive: {str(e)}")

        return self._LOREM_PATTERN.sub(replace_lorem, template)

    def _parse_now(self, template: str) -> str:
        """Process @now directive to display the current date and time."""

        def replace_now(match: Match) -> str:
            try:
                format_string = match.group("format").strip("\"'") or "%Y-%m-%d %H:%M:%S"
                alias = match.group("alias") or None
                var_name = match.group("variable")

                if alias and str(alias) != " as ":
                    raise DirectiveParsingError("Syntax error in @now directive: alias must be ' as '")

                now = datetime.now().strftime(format_string)
                if var_name:
                    self._context[var_name] = now

                return now

            except Exception as e:
                raise DirectiveParsingError(f"Error in @now directive: {str(e)}")

        return self._NOW_PATTERN.sub(replace_now, template)

    def _parse_querystring(self, template: str) -> str:
        """Process @querystring directive to modify URL query parameters."""
        from urllib.parse import parse_qs, urlencode

        def replace_querystring(match: Match) -> str:
            try:
                updates_str = match.group("updates")

                # Get current query string from context
                current_query = self._context.get("request", {}).GET.urlencode()
                query_dict = parse_qs(current_query)

                if updates_str:
                    # Parse and apply updates
                    updates = {}
                    for pair in updates_str.split(","):
                        key, value = pair.split("=")
                        updates[key.strip()] = value.strip().strip("'\"")

                    # Update query parameters
                    for key, value in updates.items():
                        if value == "None":
                            query_dict.pop(key, None)
                        else:
                            query_dict[key] = [value]

                return "?" + urlencode(query_dict, doseq=True)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @querystring directive: {str(e)}")

        return self._QUERYSTRING_PATTERN.sub(replace_querystring, template)

    def _parse_regroup(self, template: str) -> str:
        """Process @regroup directive to group a list of dictionaries by a common attribute."""
        from itertools import groupby

        def replace_regroup(match: Match) -> str:
            try:
                expression = match.group("expression")
                grouper = match.group("grouper")
                var_name = match.group("var_name")

                # Evaluate the expression to get the list
                items = eval(expression, {}, self._context)

                # Sort items by the grouper
                items = sorted(items, key=lambda x: eval(grouper, {}, {"item": x}))

                # Group items
                groups = []
                for key, group in groupby(items, key=lambda x: eval(grouper, {}, {"item": x})):
                    groups.append({"grouper": key, "list": list(group)})

                # Store result in context
                self._context[var_name] = groups
                return ""
            except Exception as e:
                raise DirectiveParsingError(f"Error in @regroup directive: {str(e)}")

        return self._REGROUP_PATTERN.sub(replace_regroup, template)

    def _parse_spaceless(self, template: str) -> str:
        """Process @spaceless directive to remove whitespace from content."""

        def replace_spaceless(match: Match) -> str:
            try:
                content = match.group("content")
                return re.sub(r"\s+", "", content)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @spaceless directive: {str(e)}")

        return self._SPACELESS_PATTERN.sub(replace_spaceless, template)

    def _parse_templatetag(self, template: str) -> str:
        """Process @templatetag directive to output a template tag."""

        def replace_templatetag(match: Match) -> str:
            try:
                tag = match.group("tag")
                return f"@{tag}"
            except Exception as e:
                raise DirectiveParsingError(f"Error in @templatetag directive: {str(e)}")

        return self._TEMPLATETAG_PATTERN.sub(replace_templatetag, template)

    def _parse_widthratio(self, template: str) -> str:
        """Process @widthratio directive to calculate a width ratio."""

        def replace_widthratio(match: Match) -> str:
            try:
                value = int(match.group("value"))
                max_value = int(match.group("max_value"))
                max_width = int(match.group("max_width"))
                return str(int(value / max_value * max_width))
            except Exception as e:
                raise DirectiveParsingError(f"Error in @widthratio directive: {str(e)}")

        return self._WIDTHRATIO_PATTERN.sub(replace_widthratio, template)

    def _parse_with(self, template: str) -> str:
        """Process @with directive to assign a value to a variable."""

        def replace_with(match: Match) -> str:
            try:
                expression = match.group("expression").strip()
                variable = self._validate_variable_name(match.group("variable").strip())
                content = match.group("content")

                # Evaluate expressions
                try:
                    value = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(f"Error evaluating with expressions '{expression}': {str(e)}")

                local_context = self._context.copy()
                local_context[variable] = value
                return self._variable_parser.parse_variables(content, local_context)

            except Exception as e:
                raise DirectiveParsingError(f"Error in @with directive: {str(e)}")

        return self._WITH_PATTERN.sub(replace_with, template)

    def _parse_csrf(self, template):
        csrf_input = self._context.get("csrf_input", "")
        return self._CSRF_PATTERN.sub(str(csrf_input), template)

    def _parse_method(self, template):

        def handle_method(match):
            method = self._validate_string(match.group("method"))
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                raise DirectiveParsingError(f"Invalid HTTP method: {method}")

            return f"""<input type="hidden" name="_method" value="{method.upper()}">"""

        return self._METHOD_PATTERN.sub(handle_method, template)

    def _parse_conditional_attributes(self, template):

        def handle_conditional_attributes(match):
            directive = match.group("directive")
            expression = match.group("expression")
            if not expression:
                expression = True

            if expression is True or (eval(expression, {}, self._context)):
                return directive if directive != "autocomplete" else "on"
            return "" if directive != "autocomplete" else "off"

        return self._CONDITIONAL_ATTRIBUTES_PATTERN.sub(handle_conditional_attributes, template)

    def _parse_static(self, template):
        pattern = re.compile(r"@static\s*\(\s*(?P<path>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_static(match), template)

    @staticmethod
    def _handle_static(match):

        try:
            from django.core.exceptions import ImproperlyConfigured
            from django.templatetags.static import static
        except ImportError:
            raise Exception("@static directive is only supported in django apps.")

        else:
            path = ast.literal_eval(match.group("path"))
            try:
                return static(path)
            except ImproperlyConfigured as exc:
                raise exc

    def _parse_error(self, template):
        """Check if an input form contains a validation error"""

        def handle_error(match):
            field_path = match.group("field")
            slot = match.group("slot")

            # Parse variables in case the field path or attributes are variables
            field_path = self._variable_parser.parse_variables(field_path, self._context)

            # Get the form field using dot notation
            parts = field_path.split(".")
            if len(parts) < 2 or len(parts) > 2:
                raise DirectiveParsingError(f"Invalid field : {field_path}. Must be in format 'form.field_name'")
            else:
                form_name, field_name = parts

            # Get the form
            form = self._context.get(form_name)
            if not form:
                raise UndefinedVariableError(f"Undefined variable '{form_name}'")

            # Get the field
            field = form.fields.get(field_name)
            if not field:
                raise AttributeError(f"{form_name} has no attribute {field_name}.")

            # Check if the field got an error
            errors = form._errors or {}

            error = errors.get(field_name)

            if error:
                local_context = self._context.copy()
                local_context["message"] = ErrorMessageContext(error)
                slot = self._variable_parser.parse_variables(slot, local_context)
                return slot

            return ""

        return self._ERROR_PATTERN.sub(handle_error, template)

    def _parse_active(self, template):
        """Use the @active('route_name', 'active_class') directive to set an active class in a nav link"""
        pattern = re.compile(r"@active\((?P<route>.*?)(?:,(?P<param>.*?))?\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_active(match), template)

    def _handle_active(self, match):
        try:
            route = ast.literal_eval(match.group("route"))
            param = ast.literal_eval(match.group("param")) if match.group("param") else "active"
        except SyntaxError as e:
            raise e
        except ValueError as e:
            raise e

        try:
            from django.urls import resolve
        except ImportError:
            raise Exception("@active directive is currenctly supported by django only")
        else:
            resolver_match = resolve(self._context.get("request").path_info)

            if route == resolver_match.url_name:
                return param
            return ""

    def _parse_field(self, template: str) -> str:
        """
        Process @field directive to render Django form fields with HTML-like attributes.

        Example:
            @field(form.email, class="form-control" id="email-input" required)

        Args:
            template: The template string

        Returns:
            The processed template with rendered form fields
        """

        def replace_field(match: Match) -> str:
            try:
                # Get field path and attributes
                field_path = match.group("field").strip()
                attrs_str = match.group("attributes").strip()

                # Parse variables in case the field path or attributes are variables
                field_path = self._variable_parser.parse_variables(field_path, self._context)
                attrs_str = self._variable_parser.parse_variables(attrs_str, self._context)

                parts = field_path.split(".")
                if len(parts) < 2 or len(parts) > 2:
                    raise DirectiveParsingError(
                        f"Invalid form field : {field_path}. Must be in format 'form.field_name'"
                    )
                else:
                    form_name, field_name = parts

                form = self._context.get(form_name)
                if not form:
                    raise UndefinedVariableError(f"Undefined variable '{form_name}'")

                # Get the field
                field = form.fields.get(field_name)
                if not field:
                    raise DirectiveParsingError(f"Field '{field_name}' not found in the form")

                # Parse HTML-like attributes
                attributes = {}

                if attrs_str:
                    attrs = attrs_str.strip().split(" ")
                    for attr in attrs:
                        if len(attr.split("=")) > 1:
                            attributes[attr.split("=")[0]] = attr.split("=")[1].strip("\"'")
                        else:
                            attributes[attr.split("=")[0]] = attr.split("=")[0]

                # Update the field widget attributes
                widget = field.widget
                widget.attrs.update(attributes)

                return form[field_name].as_widget()

            except Exception as e:
                raise DirectiveParsingError(f"Error in @field directive: {str(e)}")

        return self._FIELD_PATTERN.sub(replace_field, template)

    def _parse_liveblade(self, template):
        """
        Parse @liveblade directive to render a live blade component.

        Example:
            @liveblade('components.button', {'text': 'Click me', 'class': 'btn btn-primary'})

        Args:
            template (Template): The template string

        Returns:
            Template: The processed template with rendered live blade component

        Raises:
            DirectiveParsingError: If the component is not found
            TemplateRenderingError: If the component template has more than one root nodes
        """

        def validate_single_root_node(html_content):
            """
            Validate that an HTML component template has a single root node.

            Args:
                html_content (str): HTML content as a string

            Returns:
                bool: True if single root node, False otherwise
            """

            tags = []
            depth = 0

            # Simple state machine to track tag depth
            for match in re.finditer(r"<(/)?(\w+)[^>]*>", html_content):
                is_closing = match.group(1) == "/"
                tag = match.group(2)

                if not is_closing:
                    depth += 1
                    if depth == 1:
                        tags.append(tag)
                else:
                    depth -= 1

            # Ignore single-tag templates or templates with only whitespace
            if len(tags) <= 1:
                return True

            return False

        def handle_liveblade(match):
            component_name = self._validate_string(match.group("component"))
            liveblade = loader.load_template(f"liveblade.{component_name}")

            # Ensure the component has only one root node after removing all comments
            html_content = re.sub(r"<!--.*?-->", "", liveblade.content, flags=re.DOTALL)
            html_content = re.sub(self._COMMENT_PATTERN, "", html_content)
            html_content = re.sub(self._COMMENTS_PATTERN, "", html_content)

            if not validate_single_root_node(html_content):
                raise TemplateRenderingError("LiveBlade component must have a single root node.")

            # Render the template content
            try:
                module = importlib.import_module(f"liveblade.{component_name}")

                cls = getattr(module, f"{re.sub('[-_]', '', component_name.title())}Component")
                component = cls(f"liveblade.{component_name}")
                parsed = component.render()
                return parsed

            except ModuleNotFoundError:
                raise DirectiveParsingError(f"Component module not found: liveblade.{component_name}")

            except AttributeError as e:
                raise DirectiveParsingError(f"Error loading liveblade component: {str(e)}")

        return self._LIVEBLADE_PATTERN.sub(handle_liveblade, template)

    def _parse_translations(self, template):
        """
        Process @translate, @trans, @blocktranslate, and @plural directives in PyBlade templates.
        """

        from django.utils.translation import gettext_lazy as _
        from django.utils.translation import ngettext, pgettext

        # Handle @translate and @trans with optional context
        def replace_trans(match):
            text = match.group("text")
            translation_context = match.group("context")
            if translation_context:
                return pgettext(translation_context.strip('"'), text.strip('"'))
            return _(text.strip('"'))

        # Handle @blocktranslate with @plural and @endblocktranslate
        def replace_blocktrans(match):
            block_content = match.group("block")
            count_var = match.group("count")
            plural = None
            singular = None

            # Parse the block for @plural
            plural_match = re.search(r"(?P<singular>.*)@plural\s*(?P<plural>.*)", block_content, re.DOTALL)
            if plural_match:
                singular = plural_match.group("singular").strip()
                plural = plural_match.group("plural").strip()
            else:
                singular = block_content.strip()

            # Resolve count variable if provided
            count = int(self._context.get(count_var.strip(), 0)) if count_var else None

            # Perform translation
            if plural and count is not None:
                return ngettext(singular, plural, count)
            return _(singular)

        # Regex patterns
        translate_pattern = re.compile(
            r"@(?:trans|translate)\(\s*(?P<text>'[^']+'|\"[^\"]+\")\s*"
            r"(?:,\s*context\s*=\s*(?P<context>'[^']+'|\"[^\"]+\"))?\s*\)",
            re.DOTALL,
        )
        blocktranslate_pattern = re.compile(
            r"@blocktranslate(?:\s+count\s+(?P<count>\w+))?\s*\{(?P<block>.*?)@endblocktranslate\}", re.DOTALL
        )

        # Replace directives in content
        template = translate_pattern.sub(replace_trans, template)
        template = blocktranslate_pattern.sub(replace_blocktrans, template)

        return template

    def _parse_comment(self, template):
        return self._COMMENT_PATTERN.sub("", template)

    def _parse_verbatim_shorthand(self, template: str) -> str:
        """Process shorthand verbatim syntax (@{{ variable }})."""

        def replace_verbatim_shorthand(match: Match) -> str:
            try:
                # Remove the @ and return the content as is
                return match.group(1)
            except Exception as e:
                raise DirectiveParsingError(f"Error in verbatim shorthand: {str(e)}")

        return self._VERBATIM_SHORTHAND_PATTERN.sub(replace_verbatim_shorthand, template)

    def _parse_liveblade_scripts(self, template: str) -> str:
        """Process @liveblade_scripts directive to include Liveblade scripts."""

        def replace_liveblade_scripts(match: Match) -> str:
            try:
                attributes = match.group("attributes") or ""

                # Base scripts needed for Liveblade functionality
                scripts = [
                    '<script src="/static/liveblade/vendor/morphdom.min.js"></script>',
                    '<script src="/static/liveblade/js/scripts.js"></script>',
                    '<script src="/static/liveblade/js/advanced-directives.js"></script>',
                ]

                # Add CSRF token for security
                csrf_token = self._context.get("csrf_token", "")
                if csrf_token:
                    scripts.append(f'<meta name="csrf-token" content="{csrf_token}">')

                # Process additional attributes
                if attributes:
                    attr_dict = {}
                    for pair in attributes.split(","):
                        key, value = pair.split("=")
                        attr_dict[key.strip()] = value.strip(" '\"")

                    # Add initialization script with attributes
                    init_script = f"<script>window.liveblade.init({json.dumps(attr_dict)});</script>"
                    scripts.append(init_script)

                return "\n".join(scripts)

            except Exception as e:
                raise DirectiveParsingError(f"Error in @liveblade_scripts directive: {str(e)}")

        return self._LIVEBLADE_SCRIPTS_PATTERN.sub(replace_liveblade_scripts, template)

    def _process_bootstrap_css(self, template: str, context: Dict[str, Any]) -> str:
        """Process Bootstrap CSS directives."""

        def _get_bootstrap_css(match: Match) -> str:
            try:
                # Use static template tag for loading the CSS
                return '{% static "bootstrap/css/bootstrap.min.css" %}'
            except Exception as e:
                raise DirectiveParsingError(f"Error in bootstrap_css directive: {str(e)}")

        return self._BOOTSTRAP_CSS_PATTERN.sub(_get_bootstrap_css, template)

    def _process_bootstrap_javascript(self, template: str, context: Dict[str, Any]) -> str:
        """Process Bootstrap JavaScript directives."""

        def _get_bootstrap_js(match: Match) -> str:
            try:
                # Use static template tag for loading the JavaScript
                return '{% static "bootstrap/js/bootstrap.bundle.min.js" %}'
            except Exception as e:
                raise DirectiveParsingError(f"Error in bootstrap_javascript directive: {str(e)}")

        return self._BOOTSTRAP_JS_PATTERN.sub(_get_bootstrap_js, template)

    def _process_tailwind_css(self, template: str, context: Dict[str, Any]) -> str:
        """Process Tailwind CSS directive."""

        def _get_tailwind_css(match: Match) -> str:
            try:
                # Get the TAILWIND_APP_NAME from context or use default 'theme'
                app_name = context.get("TAILWIND_APP_NAME", "theme")
                return f'<link rel="stylesheet" href="@static(\'{app_name}/css/dist/styles.css\')">'
            except Exception as e:
                raise DirectiveParsingError(f"Error in tailwind_css directive: {str(e)}")

        return self._TAILWIND_CSS_PATTERN.sub(_get_tailwind_css, template)

    def _process_tailwind_preload_css(self, template: str, context: Dict[str, Any]) -> str:
        """Process Tailwind preload CSS directive."""

        def _get_tailwind_preload_css(match: Match) -> str:
            try:
                # Get the TAILWIND_APP_NAME from context or use default 'theme'
                app_name = context.get("TAILWIND_APP_NAME", "theme")
                return f"""<link rel="preload" href="@static('{app_name}/css/dist/styles.css')" as="style">"""
            except Exception as e:

                raise DirectiveParsingError(f"Error in tailwind_preload_css directive: {str(e)}")

        return self._TAILWIND_PRELOAD_CSS_PATTERN.sub(_get_tailwind_preload_css, template)

    def _validate_variable_name(self, name: str) -> str:
        """
        Validates if a string is a valid Python variable name.

        Args:
            name (str): The string to validate as a variable name

        Returns:
            str: The validated variable name

        Raises:
            ValueError: If the string is not a valid Python variable name
        """

        if not name:
            raise ValueError("Variable name cannot be empty")

        if name.startswith("'") or name.startswith('"'):
            name = self._validate_string(name)

        # Check if it's a Python keyword
        if keyword.iskeyword(name):
            raise ValueError(f"'{name}' is a Python keyword and cannot be used as a variable name")

        # Regular expression for valid Python variable names:
        # - Must start with letter or underscore
        # - Can only contain letters, numbers and underscores
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"

        if not re.match(pattern, name):
            raise ValueError(
                f"'{name}' is not a valid variable name. Variable names must:\n"
                "- Start with a letter or underscore\n"
                "- Contain only letters, numbers, and underscores\n"
                "- Not be a Python keyword"
            )

        return name

    def _validate_string(self, text: str) -> str:
        if (text[0], text[-1]) not in (('"', '"'), ("'", "'")):
            raise ValueError(f"{text} is not a valid string. Argument must be of type string.")
        return text[1:-1]
