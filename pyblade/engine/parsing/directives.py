"""
Directive parsing implementation for the template engine.
"""
import ast
import re
import json
from typing import Any, Dict, Match, Pattern, Tuple, Optional
from ..exceptions import DirectiveParsingError
from ..contexts import LoopContext
from .variables import VariableParser


class DirectiveParser:
    """Handles parsing and processing of template directives."""

    # Cached regex patterns
    _FOR_PATTERN: Pattern = re.compile(
        r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor",
        re.DOTALL
    )
    _IF_PATTERN: Pattern = re.compile(
        r"@(if)\s*\((.*?\)?)\)\s*(.*?)\s*(?:@(elif)\s*\((.*?\)?)\)\s*(.*?))*(?:@(else)\s*(.*?))?@(endif)",
        re.DOTALL
    )
    _UNLESS_PATTERN: Pattern = re.compile(
        r"@unless\s*\((?P<expression>.*?)\)(?P<slot>.*?)@endunless",
        re.DOTALL
    )
    _SWITCH_PATTERN: Pattern = re.compile(
        r"@(?P<directive>switch|match)\s*\((?P<expression>.*?)\)\s*(?P<cases>.*?)@end(?P=directive)",
        re.DOTALL
    )
    _CASE_PATTERN: Pattern = re.compile(
        r"@case\s*\((?P<value>.*?)\)\s*(?P<content>.*?)(?=@case|@default|@end(switch|match)|$)",
        re.DOTALL
    )
    _DEFAULT_PATTERN: Pattern = re.compile(
        r"@default\s*(?P<content>.*?)$",
        re.DOTALL
    )
    _COMMENTS_PATTERN: Pattern = re.compile(r"{#(.*?)#}", re.DOTALL)

    # New Django-like directive patterns
    _AUTOESCAPE_PATTERN: Pattern = re.compile(
        r"@autoescape\s*\((?P<mode>on|off)\)\s*(?P<content>.*?)@endautoescape",
        re.DOTALL
    )
    _CYCLE_PATTERN: Pattern = re.compile(
        r"@cycle\s*\((?P<values>.*?)\)",
        re.DOTALL
    )
    _DEBUG_PATTERN: Pattern = re.compile(
        r"@debug",
        re.DOTALL
    )
    _FILTER_PATTERN: Pattern = re.compile(
        r"@filter\s*\((?P<filters>.*?)\)\s*(?P<content>.*?)@endfilter",
        re.DOTALL
    )
    _FIRSTOF_PATTERN: Pattern = re.compile(
        r"@firstof\s*\((?P<values>.*?)(?:\s*,\s*default=(?P<default>.*?))?\)",
        re.DOTALL
    )
    _IFCHANGED_PATTERN: Pattern = re.compile(
        r"@ifchanged\s*(?:\((?P<expressions>.*?)\))?\s*(?P<content>.*?)(?:@else\s*(?P<else_content>.*?))?@endifchanged",
        re.DOTALL
    )
    _LOREM_PATTERN: Pattern = re.compile(
        r"@lorem\s*\((?P<count>\d+)(?:\s*,\s*(?P<method>w|p|b))?(?:\s*,\s*(?P<random>random))?\)",
        re.DOTALL
    )
    _NOW_PATTERN: Pattern = re.compile(
        r"@now\s*\((?P<format>.*?)\)",
        re.DOTALL
    )
    _QUERYSTRING_PATTERN: Pattern = re.compile(
        r"@querystring(?:\s*\((?P<updates>.*?)\))?",
        re.DOTALL
    )
    _REGROUP_PATTERN: Pattern = re.compile(
        r"@regroup\s*\((?P<expression>.*?)\s+by\s+(?P<grouper>.*?)\s+as\s+(?P<var_name>.*?)\)",
        re.DOTALL
    )
    _SPACELESS_PATTERN: Pattern = re.compile(
        r"@spaceless\s*(?P<content>.*?)@endspaceless",
        re.DOTALL
    )
    _TEMPLATETAG_PATTERN: Pattern = re.compile(
        r"@templatetag\s*\((?P<tag>.*?)\)",
        re.DOTALL
    )
    _WIDTHRATIO_PATTERN: Pattern = re.compile(
        r"@widthratio\s*\((?P<value>.*?)\s*,\s*(?P<max_value>.*?)\s*,\s*(?P<max_width>.*?)\)",
        re.DOTALL
    )
    _WITH_PATTERN: Pattern = re.compile(
        r"@with\s*\((?P<expressions>.*?)\)\s*(?P<content>.*?)@endwith",
        re.DOTALL
    )
    _COMMENT_PATTERN: Pattern = re.compile(
        r"@comment\s*(?P<content>.*?)@endcomment",
        re.DOTALL
    )
    _VERBATIM_PATTERN: Pattern = re.compile(
        r"@verbatim\s*(?P<content>.*?)@endverbatim",
        re.DOTALL
    )
    _VERBATIM_SHORTHAND_PATTERN: Pattern = re.compile(
        r"@({[{%].*?[%}]})",
        re.DOTALL
    )
    _COMPONENT_PATTERN: Pattern = re.compile(
        r"@component\s*\(\s*(?P<name>['\"].*?['\"])\s*(?:,\s*(?P<data>.*?))?\s*\)(?P<slot>.*?)@endcomponent",
        re.DOTALL
    )
    _LIVEBLADE_SCRIPTS_PATTERN: Pattern = re.compile(
        r"@liveblade_scripts(?:\s*\(\s*(?P<attributes>.*?)\s*\))?",
        re.DOTALL
    )

    def __init__(self):
        self._context: Dict[str, Any] = {}
        self._line_map: Dict[str, int] = {}  # Maps directive positions to line numbers
        self._variable_parser = VariableParser()

    def _get_line_number(self, template: str, position: int) -> int:
        """Get the line number for a position in the template."""
        return template.count('\n', 0, position) + 1

    def _check_unclosed_tags(self, template: str) -> None:
        """Check for unclosed directive tags and report their line numbers."""
        # Define pairs of opening and closing tags
        tag_pairs = {
            '@if': '@endif',
            '@for': '@endfor',
            '@unless': '@endunless',
            '@switch': '@endswitch'
        }
        
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
                        line_number = self._get_line_number(template, pos)
                        raise DirectiveParsingError(
                            f"Unclosed {start_tag} directive at line {line_number}"
                        )

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

        # Process directives in order
        template = self._parse_comments(template)
        template = self._parse_verbatim(template)
        template = self._parse_for(template)
        template = self._parse_if(template)
        template = self._parse_switch(template)
        template = self._parse_unless(template)
        template = self._parse_auth(template)
        template = self._parse_guest(template)
        template = self._parse_anonymous(template)

        # Django-like directives
        template = self._parse_autoescape(template)
        template = self._parse_cycle(template)
        template = self._parse_debug(template)
        template = self._parse_filter(template)
        template = self._parse_firstof(template)
        template = self._parse_ifchanged(template)
        template = self._parse_lorem(template)
        template = self._parse_now(template)
        template = self._parse_querystring(template)
        template = self._parse_regroup(template)
        template = self._parse_spaceless(template)
        template = self._parse_templatetag(template)
        template = self._parse_widthratio(template)
        template = self._parse_with(template)
        template = self._parse_component(template)
        template = self._parse_url(template)
        
        template = self._parse_csrf(template)
        template = self._parse_liveblade_scripts(template)
        return template

    def _parse_for(self, template: str) -> str:
        """Process @for loops with @empty fallback."""
        return self._FOR_PATTERN.sub(
            lambda match: self._handle_for(match),
            template
        )

    def _handle_for(self, match: Match) -> str:
        """Handle @for loop logic with proper error handling."""
        try:
            variable = match.group(1)
            iterable_expression = match.group(2)
            block = match.group(3)
            empty_block = match.group(4)

            try:
                iterable = eval(iterable_expression, {}, self._context)
            except Exception as e:
                raise DirectiveParsingError(
                    f"Error evaluating iterable expression '{iterable_expression}': {str(e)}"
                )

            if not iterable:
                return empty_block if empty_block else ""

            result = []
            current_loop = self._context.get("loop")
            loop = LoopContext(iterable, parent=current_loop)

            for index, item in enumerate(iterable):
                loop.index = index
                self._context.update({variable: item, "loop": loop})

                parsed_block = self._variable_parser.parse_variables(block, self._context)

                should_break, parsed_block = self._parse_break(parsed_block)
                should_continue, parsed_block = self._parse_continue(parsed_block)

                if should_break:
                    break
                if should_continue:
                    continue

                result.append(parsed_block)

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
                raise DirectiveParsingError(f"Error in @{directive} directive: {str(e)}")

        return self._IF_PATTERN.sub(replace_if, template)

    def _parse_unless(self, template: str) -> str:
        """Process @unless directives."""
        
        def replace_unless(match: Match) -> str:
            try:
                expression = match.group('expression')
                slot = match.group('slot')

                try:
                    condition = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(
                        f"Error evaluating unless condition '{expression}': {str(e)}"
                    )

                return "" if condition else slot

            except Exception as e:
                raise DirectiveParsingError(f"Error in @unless directive: {str(e)}")

        return self._UNLESS_PATTERN.sub(replace_unless, template)

    def _parse_switch(self, template: str) -> str:
        """Process @switch, @case, and @default directives."""
        
        def replace_switch(match: Match) -> str:
            try:
                expression = match.group('expression')
                cases_block = match.group('cases')

                # Evaluate the switch expression
                try:
                    switch_value = eval(expression, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(
                        f"Error evaluating switch expression '{expression}': {str(e)}"
                    )

                # Find all cases
                cases = self._CASE_PATTERN.finditer(cases_block)
                default_match = self._DEFAULT_PATTERN.search(cases_block)
                
                # Check each case
                for case in cases:
                    case_value = case.group('value')
                    try:
                        case_result = eval(case_value, {}, self._context)
                    except Exception as e:
                        raise DirectiveParsingError(
                            f"Error evaluating case value '{case_value}': {str(e)}"
                        )

                    if case_result == switch_value:
                        return self.parse_directives(case.group('content'), self._context)

                # If no case matched and there's a default, use it
                if default_match:
                    return self.parse_directives(default_match.group('content'), self._context)

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
                return ''  # Remove the comment and its content
            except Exception as e:
                raise DirectiveParsingError(f"Error in comment directive: {str(e)}")
        
        return self._COMMENT_PATTERN.sub(replace_comment, template)

    def _parse_verbatim(self, template: str) -> str:
        """
        Process both @verbatim blocks and shorthand verbatim (@{{ }}).
        The shorthand is processed first to prevent interference with block processing.
        """
        # First process shorthand verbatim (@{{ }})
        def replace_shorthand(match: Match) -> str:
            try:
                return match.group(1)  # Return the content without the @ prefix
            except Exception as e:
                raise DirectiveParsingError(f"Error in verbatim shorthand: {str(e)}")
        
        template = self._VERBATIM_SHORTHAND_PATTERN.sub(replace_shorthand, template)
        
        # Then process verbatim blocks
        def replace_verbatim(match: Match) -> str:
            try:
                return match.group('content')  # Return the content without processing
            except Exception as e:
                raise DirectiveParsingError(f"Error in @verbatim directive: {str(e)}")
        
        return self._VERBATIM_PATTERN.sub(replace_verbatim, template)

    def _parse_url(self, template: str) -> str:
        """Process @url directive with support for Django-style 'as' variable assignment."""
        def replace_url(match: Match) -> str:
            try:
                url_pattern = match.group('pattern').strip('\'"')
                params = match.group('params')
                as_var = match.group('as_var')
                
                # Build URL parameters
                url_params = []
                if params:
                    for param in params.split(','):
                        param = param.strip()
                        if '=' in param:
                            key, value = param.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            try:
                                # Evaluate the value in the current context
                                evaluated_value = eval(value, {}, self._context)
                                url_params.append((key, evaluated_value))
                            except Exception as e:
                                raise DirectiveParsingError(f"Error evaluating URL parameter '{value}': {str(e)}")
                
                # Get URL patterns from context
                urlconf = self._context.get('urlconf', None)
                if not urlconf:
                    raise DirectiveParsingError("URL configuration not found in context")
                
                try:
                    # Resolve URL pattern
                    from django.urls import reverse
                    url = reverse(url_pattern, args=[p[1] for p in url_params if not p[0]], 
                                kwargs={p[0]: p[1] for p in url_params if p[0]})
                    
                    # If 'as' variable is specified, store in context and return empty string
                    if as_var:
                        self._context[as_var.strip()] = url
                        return ''
                    return url
                    
                except Exception as e:
                    raise DirectiveParsingError(f"Error resolving URL '{url_pattern}': {str(e)}")
                
            except Exception as e:
                raise DirectiveParsingError(f"Error in @url directive: {str(e)}")
        
        # Updated pattern to support 'as' variable assignment
        url_pattern = re.compile(
            r"@url\s*\(\s*(?P<pattern>['\"].*?['\"])\s*(?:,\s*(?P<params>.*?))?\s*(?:\s+as\s+(?P<as_var>\w+))?\s*\)",
            re.DOTALL
        )
        
        return url_pattern.sub(replace_url, template)

    @staticmethod
    def _parse_break(template: str) -> Tuple[bool, str]:
        """Process @break directives."""
        pattern = re.compile(r"@break(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, self._context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @break directive: {str(e)}")
        return False, template

    @staticmethod
    def _parse_continue(template: str) -> Tuple[bool, str]:
        """Process @continue directives."""
        pattern = re.compile(r"@continue(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match:
            template = pattern.sub("", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            try:
                if eval(expression, {}, self._context):
                    return True, template
            except Exception as e:
                raise DirectiveParsingError(f"Error in @continue directive: {str(e)}")
        return False, template


    # TODO : Update parsers

    def _parse_auth_or_guest(self, template):
        """
        Generalized method to parse @auth or @guest directives.
        """
        def handle_auth_or_guest(match):
            """
            Generalized handler for @auth and @guest directives.
            """
            directive = match.group('directive')

            is_authenticated = False
            request = self._context.get("request", None)
            if request:
                try:
                    is_authenticated = request.user.is_authenticated
                except Exception as e:
                    raise Exception(str(e))

            should_render_first_block = (
                is_authenticated if directive == "auth" else not is_authenticated
            )

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


    def _parse_include(self, template):
        """Find partials code to include in the template"""

        pattern = re.compile(r"@include\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
        match = re.search(pattern, template)

        if match is not None:
            file_name = match.group(1) if match else None
            partial_template = loader.load_template(file_name) if file_name else None

            if partial_template:
                # Parse the content to include before replacement
                partial_template = self.parse(str(partial_template), self._context)
                return re.sub(pattern, partial_template, template)

        return template

    def _parse_extends(self, template):
        """Search for extends directive in the template then parse sections inside."""

        pattern = re.compile(r"(.*?)@extends\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
        match = re.match(pattern, template)

        if match:
            if match.group(1):
                raise Exception("The @extend tag must be at the top of the file before any character.")

            layout_name = match.group(2) if match else None
            if not layout_name:
                raise Exception("Layout not found")

            try:
                layout = loader.load_template(layout_name)
                self.parse(str(layout), self._context)
                return self._parse_section(template, str(layout))
            except Exception as e:
                raise e

        return template

    def _parse_section(self, template, layout):
        """
        Find every section that can be yielded in the layout.
        Sections may be inside @section(<name>) and @endsection directives, or inside
        @block(<name>) and @endblock directives.

        :param template: The partial template content
        :param layout: The layout content in which sections will be yielded
        :return: The full page after yield
        """

        directives = ("section", "block")

        local_context = {}
        for directive in directives:
            pattern = re.compile(
                rf"@{directive}\s*\((?P<section_name>[^)]*)\)\s*(?P<content>.*?)@end{directive}", re.DOTALL
            )

            matches = pattern.findall(template)

            for match in matches:
                argument, content = match
                line_match_pattern = re.compile(rf"@{directive}\s*\(({argument})\)", re.DOTALL)
                section_name = self._validate_argument(line_match_pattern.search(template))

                local_context[section_name] = content
                # TODO: Add a slot variable that will contain all the content outside the @section directives

        return self._parse_yield(layout)

    def _parse_yield(self, layout):
        """
        Replace every yieldable content by the actual value or None

        :param layout:
        :return:
        """
        pattern = re.compile(r"@yield\s*\(\s*(?P<yieldable_name>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_yield(match), layout)

    def _handle_yield(self, match):
        yieldable_name = self._validate_argument(match)
        return self._context.get(yieldable_name)

    def _parse_pyblade_tags(self, template, context):
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

        component, props = self._parse_props(str(component))
        component_context.update(attributes)
        attributes = AttributesContext(props, attributes, component_context)

        component_context["slot"] = SlotContext(match.group("slot"))
        component_context["attributes"] = attributes
        parsed_component = self.parse(component, component_context)

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

    def _parse_class(self, template):
        pattern = re.compile(r"@class\s*\((?P<dictionary>.*?)\s*\)", re.DOTALL)

        match = pattern.search(template)
        if match:
            try:
                attrs = eval(match.group("dictionary"), {}, self._context)
            except SyntaxError as e:
                raise e
            except ValueError as e:
                raise e
            else:
                classes = ClassContext(attrs, self._context)
                return re.sub(pattern, str(classes), template)
        return template

    def _parse_autoescape(self, template: str) -> str:
        """Process @autoescape directive for controlling HTML escaping."""
        def replace_autoescape(match: Match) -> str:
            try:
                mode = match.group('mode')
                content = match.group('content')
                
                # Store current autoescape setting
                current_autoescape = self._context.get('autoescape', True)
                
                # Update context with new autoescape setting
                self._context['autoescape'] = (mode == 'on')
                
                # Process content with new autoescape setting
                result = self.parse_directives(content, self._context)
                
                # Restore previous autoescape setting
                self._context['autoescape'] = current_autoescape
                
                return result
            except Exception as e:
                raise DirectiveParsingError(f"Error in @autoescape directive: {str(e)}")
        
        return self._AUTOESCAPE_PATTERN.sub(replace_autoescape, template)

    def _parse_cycle(self, template: str) -> str:
        """Process @cycle directive for cycling through a list of values."""
        def replace_cycle(match: Match) -> str:
            try:
                values_str = match.group('values')
                values = [v.strip() for v in values_str.split(',')]
                
                # Get or initialize cycle counter
                cycle_counter = self._context.setdefault('_cycle_counter', {})
                cycle_key = f"cycle_{values_str}"
                
                if cycle_key not in cycle_counter:
                    cycle_counter[cycle_key] = 0
                else:
                    cycle_counter[cycle_key] = (cycle_counter[cycle_key] + 1) % len(values)
                
                return str(values[cycle_counter[cycle_key]])
            except Exception as e:
                raise DirectiveParsingError(f"Error in @cycle directive: {str(e)}")
        
        return self._CYCLE_PATTERN.sub(replace_cycle, template)

    def _parse_debug(self, template: str) -> str:
        """Process @debug directive to output debugging information."""
        def replace_debug(match: Match) -> str:
            try:
                debug_info = []
                for key, value in sorted(self._context.items()):
                    if not key.startswith('_'):  # Skip internal variables
                        debug_info.append(f"{key}: {repr(value)}")
                return '\n'.join(debug_info)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @debug directive: {str(e)}")
        
        return self._DEBUG_PATTERN.sub(replace_debug, template)

    def _parse_filter(self, template: str) -> str:
        """Process @filter directive to apply filters to content."""
        def replace_filter(match: Match) -> str:
            try:
                filters = match.group('filters').split('|')
                content = match.group('content')
                
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
                values = [v.strip() for v in match.group('values').split(',')]
                default = match.group('default')
                
                for value in values:
                    try:
                        result = eval(value, {}, self._context)
                        if result:
                            return str(result)
                    except:
                        continue
                
                return str(default) if default else ''
            except Exception as e:
                raise DirectiveParsingError(f"Error in @firstof directive: {str(e)}")
        
        return self._FIRSTOF_PATTERN.sub(replace_firstof, template)

    def _parse_ifchanged(self, template: str) -> str:
        """Process @ifchanged directive to conditionally output content if it has changed."""
        def replace_ifchanged(match: Match) -> str:
            try:
                expressions = match.group('expressions')
                content = match.group('content')
                else_content = match.group('else_content')
                
                # Initialize storage for last values if not present
                if '_ifchanged_last_values' not in self._context:
                    self._context['_ifchanged_last_values'] = {}
                
                # Generate a unique key for this ifchanged block
                key = f"ifchanged_{hash(content)}"
                
                if expressions:
                    # Watch for changes in specific variables
                    current_values = tuple(eval(expr.strip(), {}, self._context) 
                                        for expr in expressions.split(','))
                else:
                    # Watch for changes in the rendered content
                    current_values = (self.parse_directives(content, self._context),)
                
                last_values = self._context['_ifchanged_last_values'].get(key)
                
                if last_values != current_values:
                    self._context['_ifchanged_last_values'][key] = current_values
                    return self.parse_directives(content, self._context)
                elif else_content:
                    return self.parse_directives(else_content, self._context)
                return ''
                
            except Exception as e:
                raise DirectiveParsingError(f"Error in @ifchanged directive: {str(e)}")
        
        return self._IFCHANGED_PATTERN.sub(replace_ifchanged, template)

    def _parse_lorem(self, template: str) -> str:
        """Process @lorem directive to generate Lorem Ipsum text."""
        import random
        
        WORDS = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", 
                "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore",
                "et", "dolore", "magna", "aliqua"]
        
        def generate_words(count: int, random_order: bool = False) -> str:
            words = WORDS.copy()
            if random_order:
                random.shuffle(words)
            while len(words) < count:
                words.extend(WORDS)
            return ' '.join(words[:count])
        
        def generate_paragraphs(count: int, random_order: bool = False) -> str:
            paragraphs = []
            for _ in range(count):
                words = generate_words(random.randint(20, 100), random_order)
                paragraphs.append(words.capitalize() + '.')
            return '\n\n'.join(paragraphs)
        
        def replace_lorem(match: Match) -> str:
            try:
                count = int(match.group('count'))
                method = match.group('method') or 'w'
                random_order = bool(match.group('random'))
                
                if method == 'w':
                    return generate_words(count, random_order)
                elif method == 'p':
                    return generate_paragraphs(count, random_order)
                elif method == 'b':
                    return f'<p>{generate_paragraphs(count, random_order)}</p>'
                else:
                    raise DirectiveParsingError(f"Invalid lorem method: {method}")
                
            except Exception as e:
                raise DirectiveParsingError(f"Error in @lorem directive: {str(e)}")
        
        return self._LOREM_PATTERN.sub(replace_lorem, template)

    def _parse_now(self, template: str) -> str:
        """Process @now directive to display the current date and time."""
        from datetime import datetime
        
        def replace_now(match: Match) -> str:
            try:
                format_string = match.group('format').strip('"\'')
                return datetime.now().strftime(format_string)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @now directive: {str(e)}")
        
        return self._NOW_PATTERN.sub(replace_now, template)

    def _parse_querystring(self, template: str) -> str:
        """Process @querystring directive to modify URL query parameters."""
        from urllib.parse import parse_qs, urlencode
        
        def replace_querystring(match: Match) -> str:
            try:
                updates_str = match.group('updates')
                
                # Get current query string from context
                current_query = self._context.get('request', {}).get('query_string', '')
                query_dict = parse_qs(current_query)
                
                if updates_str:
                    # Parse and apply updates
                    updates = {}
                    for pair in updates_str.split(','):
                        key, value = pair.split('=')
                        updates[key.strip()] = value.strip()
                    
                    # Update query parameters
                    for key, value in updates.items():
                        if value == 'None':
                            query_dict.pop(key, None)
                        else:
                            query_dict[key] = [value]
                
                return '?' + urlencode(query_dict, doseq=True)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @querystring directive: {str(e)}")
        
        return self._QUERYSTRING_PATTERN.sub(replace_querystring, template)

    def _parse_regroup(self, template: str) -> str:
        """Process @regroup directive to group a list of dictionaries by a common attribute."""
        from itertools import groupby
        from operator import itemgetter
        
        def replace_regroup(match: Match) -> str:
            try:
                expression = match.group('expression')
                grouper = match.group('grouper')
                var_name = match.group('var_name')
                
                # Evaluate the expression to get the list
                items = eval(expression, {}, self._context)
                
                # Sort items by the grouper
                items = sorted(items, key=lambda x: eval(grouper, {}, {'item': x}))
                
                # Group items
                groups = []
                for key, group in groupby(items, key=lambda x: eval(grouper, {}, {'item': x})):
                    groups.append({
                        'grouper': key,
                        'list': list(group)
                    })
                
                # Store result in context
                self._context[var_name] = groups
                return ''
            except Exception as e:
                raise DirectiveParsingError(f"Error in @regroup directive: {str(e)}")
        
        return self._REGROUP_PATTERN.sub(replace_regroup, template)

    def _parse_spaceless(self, template: str) -> str:
        """Process @spaceless directive to remove whitespace from content."""
        def replace_spaceless(match: Match) -> str:
            try:
                content = match.group('content')
                return re.sub(r'\s+', '', content)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @spaceless directive: {str(e)}")
        
        return self._SPACELESS_PATTERN.sub(replace_spaceless, template)

    def _parse_templatetag(self, template: str) -> str:
        """Process @templatetag directive to output a template tag."""
        def replace_templatetag(match: Match) -> str:
            try:
                tag = match.group('tag')
                return f"{{% {tag} %}}"
            except Exception as e:
                raise DirectiveParsingError(f"Error in @templatetag directive: {str(e)}")
        
        return self._TEMPLATETAG_PATTERN.sub(replace_templatetag, template)

    def _parse_widthratio(self, template: str) -> str:
        """Process @widthratio directive to calculate a width ratio."""
        def replace_widthratio(match: Match) -> str:
            try:
                value = int(match.group('value'))
                max_value = int(match.group('max_value'))
                max_width = int(match.group('max_width'))
                return str(int(value / max_value * max_width))
            except Exception as e:
                raise DirectiveParsingError(f"Error in @widthratio directive: {str(e)}")
        
        return self._WIDTHRATIO_PATTERN.sub(replace_widthratio, template)

    def _parse_with(self, template: str) -> str:
        """Process @with directive to assign a value to a variable."""
        def replace_with(match: Match) -> str:
            try:
                expressions = match.group('expressions')
                content = match.group('content')
                
                # Evaluate expressions
                try:
                    expressions = eval(expressions, {}, self._context)
                except Exception as e:
                    raise DirectiveParsingError(
                        f"Error evaluating with expressions '{expressions}': {str(e)}"
                    )
                
                # Assign values to variables
                for var, value in expressions.items():
                    self._context[var] = value
                
                # Process content
                return self.parse_directives(content, self._context)
            except Exception as e:
                raise DirectiveParsingError(f"Error in @with directive: {str(e)}")
        
        return self._WITH_PATTERN.sub(replace_with, template)

    def _parse_csrf(self, template):
        pattern = re.compile(r"@csrf", re.DOTALL)
        token = self._context.get("csrf_token", "")

        return pattern.sub(f"""<input type="hidden" name="csrfmiddlewaretoken" value="{token}">""", template)

    def _parse_method(self, template):
        pattern = re.compile(r"@method\s*\(\s*(?P<method>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_method(match), template)

    def _handle_method(self, match):
        method = self._validate_argument(match)
        return f"""<input type="hidden" name="_method" value="{method}">"""

    def _parse_static(self, template, context):
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

    def _parse_url(self, template):
        pattern = re.compile(r"@url\s*\(\s*(?P<name>.*?)\s*(?:,(?P<params>.*?))?\)")

        return pattern.sub(lambda match: self._handle_url(match), template)

    def _handle_url(self, match):
        # Check django installation
        try:
            from django.core.exceptions import ImproperlyConfigured
            from django.urls import reverse
        except ImportError:
            raise Exception("@url directive is only supported in django projects.")

        route_name = match.group("name")
        params = match.group("params")

        # Check route name is a valid string
        try:
            route_name = ast.literal_eval(route_name)
        except SyntaxError:
            raise Exception(
                f"Syntax error: The route name must be a valid string. Got {route_name} near line "
                f"{self._get_line_number(match)}"
            )

        # Try return the route url or raise errors if bad configuration encountered
        try:
            if params:
                try:
                    params = eval(params, {}, self._context)
                    params = ast.literal_eval(str(params))
                except (SyntaxError, ValueError) as e:
                    raise Exception(str(e))
                else:
                    if isinstance(params, dict):
                        return reverse(route_name, kwargs=params)
                    elif isinstance(params, list):
                        return reverse(route_name, args=params)
                    else:
                        raise Exception("The url parameters must be of type list or dict")
            return reverse(route_name)
        except ImproperlyConfigured as e:
            raise Exception(str(e))

    def _checked_selected_required(self, template, context):
        pattern = re.compile(r"@(?P<directive>checked|selected|required)\s*\(\s*(?P<expression>.*?)\s*\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_csr(match, context), template)

    @staticmethod
    def _handle_csr(match):
        directive = match.group("directive")
        expression = match.group("expression")
        if not (eval(expression, {}, self._context)):
            return ""
        return directive

    def _parse_error(self, template):
        """Check if an input form contains a validation error"""
        pattern = re.compile(r"@error\s*\((?P<field>.*?)\)\s*(?P<slot>.*?)\s*@enderror", re.DOTALL)

        return pattern.sub(lambda match: self._handle_error(match, self._context), template)

    def _handle_error(self, match):
        field = match.group("field")
        slot = match.group("slot")

        message = eval(field, {}, self._context)
        if message:
            local_context = self._context.copy()
            local_context["message"] = message
            rendered = self.parse(slot, local_context)

            return rendered

        return ""

    def _parse_active(self, template):
        """Use the @active('route_name', 'active_class') directive to set an active class in a nav link"""
        pattern = re.compile(r"@active\((?P<route>.*?)(?:,(?P<param>.*?))?\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_active(match, self._context), template)

    @staticmethod
    def _handle_active(match):
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
            resolver_match = resolve(context.get('request').path_info)

            if route == resolver_match.url_name:
                return param
            return ""

    def _parse_field(self, template):
        """To render an input field with custom attributes"""
        pass


    @staticmethod
    def _handle_csr(match):
        directive = match.group("directive")
        expression = match.group("expression")
        if not (eval(expression, {}, self._context)):
            return ""
        return directive

    def _parse_component(self):
        pass

    def _parse_liveblade(self, template, context):
        pattern = re.compile(r"@liveblade\s*\(\s*(?P<component>.*?)\s*\)")
        match = re.search(pattern, template)

        if match is not None:
            component = ast.literal_eval(match.group("component"))
            component_content = loader.load_template(f"liveblade.{component}") if component else None

            if component_content:
                # Add pyblade id to the parent tag of the component
                tag_pattern = re.compile(r"<(?P<tag>\w+)\s*(?P<attributes>.*?)>(.*)</(?P=tag)", re.DOTALL)

                m = re.search(tag_pattern, str(component_content))
                attributes = m.group("attributes")
                component_content = re.sub(attributes, f'{attributes} liveblade_id="{component}"', str(component_content))

                # Parse the content to include before replacement
                try:
                    import importlib

                    module = importlib.import_module(f"components.{component}")
                    cls = getattr(module, "".join([word.capitalize() for word in component.split('_')]))

                    parsed = cls().render()
                    return re.sub(pattern, parsed, template)
                except ModuleNotFoundError as e:
                    raise e
                except AttributeError as e:
                    raise e
                except Exception as e:
                    raise e

        return template

    def _parse_translations(slef, template, context):
        """
        Process @translate, @trans, @blocktranslate, and @plural directives in PyBlade templates.
        """

        # Handle @translate and @trans with optional context
        def replace_trans(match):
            text = match.group('text')
            translation_context = match.group('context')
            if translation_context:
                return pgettext(translation_context.strip('"'), text.strip('"'))
            return _(text.strip('"'))

        # Handle @blocktranslate with @plural and @endblocktranslate
        def replace_blocktrans(match):
            block_content = match.group('block')
            count_var = match.group('count')
            plural = None
            singular = None

            # Parse the block for @plural
            plural_match = re.search(r'(?P<singular>.*)@plural\s*(?P<plural>.*)', block_content, re.DOTALL)
            if plural_match:
                singular = plural_match.group('singular').strip()
                plural = plural_match.group('plural').strip()
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
            r"@(?:trans|translate)\(\s*(?P<text>'[^']+'|\"[^\"]+\")\s*(?:,\s*context\s*=\s*(?P<context>'[^']+'|\"[^\"]+\"))?\s*\)"
        )
        blocktranslate_pattern = re.compile(
            r"@blocktranslate(?:\s+count\s+(?P<count>\w+))?\s*\{(?P<block>.*?)@endblocktranslate\}",
            re.DOTALL
        )

        # Replace directives in content
        template = translate_pattern.sub(replace_trans, template)
        template = blocktranslate_pattern.sub(replace_blocktrans, template)

        return template

    def _validate_argument(self, match):

        argument = match.group(1)
        if (argument[0], argument[-1]) not in (('"', '"'), ("'", "'")) or len(argument.split(" ")) > 1:
            raise Exception(
                f"{argument} is not a valid string. Argument must be of type string."
                f"Look at line {self._get_line_number(match)}"
            )
        return argument[1:-1]

    def _parse_comment(self, template):
        return self._COMMENT_PATTERN.sub("", template)

    def _parse_verbatim(self, template):
        return self._VERBATIM_PATTERN.sub(lambda match: match.group("content"), template)

    def _parse_verbatim_shortcut(self, template):
        return self._VERBATIM_SHORTHAND_PATTERN.sub(lambda match: match.group(0)[1:-1], template)

    def _parse_component(self, template):
        return self._COMPONENT_PATTERN.sub(lambda match: self._handle_component(match), template)

    def _handle_component(self, match):
        name = match.group("name")
        data = match.group("data")
        slot = match.group("slot")

        try:
            import importlib

            module = importlib.import_module(f"components.{name}")
            cls = getattr(module, "".join([word.capitalize() for word in name.split('_')]))

            props = {}
            if data:
                props = eval(data, {}, self._context)

            return cls(props).render(slot)
        except ModuleNotFoundError as e:
            raise e
        except AttributeError as e:
            raise e
        except Exception as e:
            raise e

    def _parse_liveblade_scripts(self, template):
        return self._LIVEBLADE_SCRIPTS_PATTERN.sub(lambda match: self._handle_liveblade_scripts(match), template)

    def _handle_liveblade_scripts(self, match):
        attributes = match.group("attributes")

        try:
            import importlib

            module = importlib.import_module("liveblade_scripts")
            cls = getattr(module, "LivebladeScripts")

            props = {}
            if attributes:
                props = eval(attributes, {}, self._context)

            return cls(props).render()
        except ModuleNotFoundError as e:
            raise e
        except AttributeError as e:
            raise e
        except Exception as e:
            raise e

    def _parse_verbatim_shorthand(self, template: str) -> str:
        """Process shorthand verbatim syntax (@{{ variable }})."""
        def replace_verbatim_shorthand(match: Match) -> str:
            try:
                # Remove the @ and return the content as is
                return match.group(1)
            except Exception as e:
                raise DirectiveParsingError(f"Error in verbatim shorthand: {str(e)}")
        
        return self._VERBATIM_SHORTHAND_PATTERN.sub(replace_verbatim_shorthand, template)

    def _parse_component(self, template: str) -> str:
        """Process @component directive for reusable template components."""
        def replace_component(match: Match) -> str:
            try:
                name = self._validate_argument(match.group('name'))
                data = match.group('data')
                slot = match.group('slot')
                
                # Get the component template
                component_path = f"components/{name}.html"
                try:
                    with open(component_path, 'r') as f:
                        component_template = f.read()
                except FileNotFoundError:
                    raise DirectiveParsingError(f"Component not found: {component_path}")
                
                # Create component context
                component_context = self._context.copy()
                
                # Add slot content to context
                component_context['slot'] = slot
                
                # Process data arguments
                if data:
                    try:
                        # Convert string data to dict
                        data_dict = {}
                        for pair in data.split(','):
                            key, value = pair.split('=')
                            key = key.strip()
                            value = value.strip()
                            # Evaluate the value in the current context
                            data_dict[key] = eval(value, {}, self._context)
                        component_context.update(data_dict)
                    except Exception as e:
                        raise DirectiveParsingError(f"Error processing component data: {str(e)}")
                
                # Process the component template with the new context
                return self.parse_directives(component_template, component_context)
                
            except Exception as e:
                raise DirectiveParsingError(f"Error in @component directive: {str(e)}")
        
        return self._COMPONENT_PATTERN.sub(replace_component, template)

    def _parse_liveblade_scripts(self, template: str) -> str:
        """Process @liveblade_scripts directive to include Liveblade scripts."""
        def replace_liveblade_scripts(match: Match) -> str:
            try:
                attributes = match.group('attributes') or ''
                
                # Base scripts needed for Liveblade functionality
                scripts = [
                    '<script src="/static/js/liveblade.js"></script>',
                    '<script>window.liveblade = new Liveblade();</script>'
                ]
                
                # Add CSRF token for security
                csrf_token = self._context.get('csrf_token', '')
                if csrf_token:
                    scripts.append(
                        f'<meta name="csrf-token" content="{csrf_token}">'
                    )
                
                # Process additional attributes
                if attributes:
                    attr_dict = {}
                    for pair in attributes.split(','):
                        key, value = pair.split('=')
                        attr_dict[key.strip()] = value.strip(' \'"')
                    
                    # Add initialization script with attributes
                    init_script = f'<script>window.liveblade.init({json.dumps(attr_dict)});</script>'
                    scripts.append(init_script)
                
                return '\n'.join(scripts)
                
            except Exception as e:
                raise DirectiveParsingError(f"Error in @liveblade_scripts directive: {str(e)}")
        
        return self._LIVEBLADE_SCRIPTS_PATTERN.sub(replace_liveblade_scripts, template)
