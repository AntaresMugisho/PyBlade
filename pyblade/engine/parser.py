import ast
import html
import re

from django.utils.translation import gettext as _, ngettext, pgettext

from . import loader
from .contexts import AttributesContext, ClassContext, LoopContext, SlotContext
from .exceptions import UndefinedVariableError


class Parser:

    def __init__(self):
        self.directives = {
            "comments": self._parse_comments,
            "for": self._parse_for,
            "if": self._parse_if,
            "csrf": self._parse_csrf,
            "method": self._parse_method,
            "checked_selected_required": self._checked_selected_required,
            "active": self._parse_active,
            "error": self._parse_error,
            "class": self._parse_class,
            "url": self._parse_url,
            "static": self._parse_static,
            "auth": self._parse_auth,
            "extends": self._parse_extends,
            "include": self._parse_include,
            "liveblade": self._parse_liveblade,
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

        template = self._parse_pyblade_tags(template, context)

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

        # SlotContext AttributesContext and ClassContext variables must not be escaped anyway
        if isinstance(variable_value, (SlotContext, AttributesContext, ClassContext)):
            escape = False

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
            r"@(if)\s*\((.*?\)?)\)\s*(.*?)\s*(?:@(elif)\s*\((.*?\)?)\)\s*(.*?))*(?:@(else)\s*(.*?))?@(endif)", re.DOTALL
        )
        return pattern.sub(lambda match: self._handle_if(match, context), template)

    def _handle_if(self, match, context):
        captures = [group for group in match.groups()]

        for i, capture in enumerate(captures[:-1]):
            if capture in ("if", "elif", "else", "auth"):
                if capture in ("if", "elif"):
                    if eval(captures[i + 1], {}, context):
                        return captures[i + 2]
                else:
                    return captures[i + 1]

    def _parse_auth_or_guest(self, template, context):
        """
        Generalized method to parse @auth or @guest directives.
        """
        pattern = re.compile(
            r"@(?P<directive>auth|guest|anonymous)\s*(.*?)\s*(?:@(else)\s*(.*?))?\s*@end(?P=directive)", re.DOTALL
        )
        return pattern.sub(lambda match: self._handle_auth_or_guest(match, context), template)

    @staticmethod
    def _handle_auth_or_guest(match, context):
        """
        Generalized handler for @auth and @guest directives.
        """
        directive = match.group('directive')

        is_authenticated = False
        request = context.get("request", None)
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

    def _parse_auth(self, template, context):
        """Check if the user is authenticated."""
        return self._parse_auth_or_guest(template, context)

    def _parse_guest(self, template, context):
        """Check if the user is not authenticated."""
        return self._parse_auth_or_guest(template, context)

    def _parse_anonymous(self, template, context):
        """Check if the user is not authenticated. Same as @guest"""
        return self._parse_auth_or_guest(template, context)

    def _parse_for(self, template, context):
        """Handle @for, @empty and @endfor directives."""

        pattern = re.compile(r"@for\s*\((.*?)\s+in\s+(.*?)\)\s*(.*?)(?:@empty\s*(.*?))?@endfor", re.DOTALL)
        return pattern.sub(lambda match: self._handle_for(match, context), template)

    def _handle_for(self, match, context):
        """Executes the for logic."""
        variable = match.group(1)
        iterable_expression = match.group(2)
        block = match.group(3)
        empty_block = match.group(4)

        try:
            iterable = eval(iterable_expression, {}, context)
        except Exception as e:
            raise ValueError(f"Error evaluating iterable expression '{iterable_expression}': {e}")

        # Handle empty iterable
        if not iterable:
            return empty_block if empty_block else ""

        result = []
        current_loop = context.get("loop")  # Get the parent loop if any
        loop = LoopContext(iterable, parent=current_loop)

        for index, item in enumerate(iterable):
            loop.index = index

            # Update local context for this iteration
            local_context = {
                **context,
                variable: item,
                "loop": loop,
            }

            # Re parse block to process nested loops
            parsed_block = self.parse(block, local_context)
            should_break, parsed_block = self._parse_break(parsed_block, local_context)
            should_continue, parsed_block = self._parse_continue(parsed_block, local_context)

            # Check for break and continue keywords before adding the block in the result
            if should_break:
                break

            if should_continue:
                continue

            result.append(parsed_block)


        return "".join(result)

    @staticmethod
    def _parse_break(template, context):
        pattern = re.compile(r"@break(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match :
            template = re.sub(pattern, "", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            elif eval(expression, {}, context):
                return True, template
        return False, template

    @staticmethod
    def _parse_continue(template, context):
        pattern = re.compile(r"@continue(?:\s*\(\s*(?P<expression>.*?)\s*\))?", re.DOTALL)
        match = pattern.search(template)

        if match :
            template = re.sub(pattern, "", template)
            expression = match.group("expression")
            if not expression:
                return True, template
            elif eval(expression, {}, context):
                return True, template
        return False, template


    def _parse_include(self, template, context):
        """Find partials code to include in the template"""

        pattern = re.compile(r"@include\s*\(\s*[\"']?(.*?(?:\.?\.*?)*)[\"']?\s*\)", re.DOTALL)
        match = re.search(pattern, template)

        if match is not None:
            file_name = match.group(1) if match else None
            partial_template = loader.load_template(file_name) if file_name else None

            if partial_template:
                # Parse the content to include before replacement
                partial_template = self.parse(str(partial_template), context)
                return re.sub(pattern, partial_template, template)

        return template

    def _parse_extends(self, template, context):
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
                self.parse(str(layout), context)
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

    def _parse_pyblade_tags(self, template, context):
        pattern = re.compile(
            r"<b-(?P<component>\w+-?\w+)\s*(?P<attributes>.*?)\s*(?:/>|>(?P<slot>.*?)</b-(?P=component)>)", re.DOTALL
        )
        return pattern.sub(lambda match: self._handle_pyblade_tags(match, context), template)

    def _handle_pyblade_tags(self, match, context):
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
                    value = eval(value, {}, context) if value else None
                except NameError as e:
                    raise e

                component_context[name] = value

            attributes[name] = value

        component, props = self._parse_props(str(component), context)
        component_context.update(attributes)
        attributes = AttributesContext(props, attributes, component_context)

        component_context["slot"] = SlotContext(match.group("slot"))
        component_context["attributes"] = attributes
        parsed_component = self.parse(component, component_context)

        return parsed_component

    def _parse_props(self, component: str, context) -> tuple:
        pattern = re.compile(r"@props\s*\((?P<dictionary>.*?)\s*\)", re.DOTALL)
        match = pattern.search(component)

        props = {}
        if match:
            component = re.sub(pattern, "", component)
            dictionary = match.group("dictionary")
            try:
                props = eval(dictionary, {}, context)
            except SyntaxError as e:
                raise e
            except ValueError as e:
                raise e

        return component, props

    def _parse_class(self, template, context):
        pattern = re.compile(r"@class\s*\((?P<dictionary>.*?)\s*\)", re.DOTALL)

        match = pattern.search(template)
        if match:
            try:
                attrs = eval(match.group("dictionary"), {}, context)
            except SyntaxError as e:
                raise e
            except ValueError as e:
                raise e
            else:
                classes = ClassContext(attrs, context)
                return re.sub(pattern, str(classes), template)
        return template

    def _validate_argument(self, match):

        argument = match.group(1)
        if (argument[0], argument[-1]) not in (('"', '"'), ("'", "'")) or len(argument.split(" ")) > 1:
            raise Exception(
                f"{argument} is not a valid string. Argument must be of type string."
                f"Look at line {self._get_line_number(match)}"
            )
        return argument[1:-1]

    def _parse_csrf(self, template, context):
        pattern = re.compile(r"@csrf", re.DOTALL)
        token = context.pop("csrf_token", "")

        return pattern.sub(f"""<input type="hidden" name="csrfmiddlewaretoken" value="{token}">""", template)

    def _parse_method(self, template, context):
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

    def _parse_url(self, template, context):
        pattern = re.compile(r"@url\s*\(\s*(?P<name>.*?)\s*(?:,(?P<params>.*?))?\)")

        return pattern.sub(lambda match: self._handle_url(match, context), template)

    def _handle_url(self, match, context):
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
                    params = eval(params, {}, context)
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
    def _handle_csr(match, context):
        directive = match.group("directive")
        expression = match.group("expression")
        if not (eval(expression, {}, context)):
            return ""
        return directive

    def _parse_error(self, template, context):
        """Check if an input form contains a validation error"""
        pattern = re.compile(r"@error\s*\((?P<field>.*?)\)\s*(?P<slot>.*?)\s*@enderror", re.DOTALL)

        return pattern.sub(lambda match: self._handle_error(match, context), template)

    def _handle_error(self, match, context):
        field = match.group("field")
        slot = match.group("slot")

        message = eval(field, {}, context)
        if message:
            local_context = context.copy()
            local_context["message"] = message
            rendered = self.parse(slot, local_context)

            return rendered

        return ""

    def _parse_active(self, template, context):
        """Use the @active('route_name', 'active_class') directive to set an active class in a nav link"""
        pattern = re.compile(r"@active\((?P<route>.*?)(?:,(?P<param>.*?))?\)", re.DOTALL)
        return pattern.sub(lambda match: self._handle_active(match, context), template)

    @staticmethod
    def _handle_active(match, context):
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

    def _parse_field(self, template, context):
        """To render an input field with custom attributes"""
        pass

    @staticmethod
    def _parse_comments(template, context):
        pattern = re.compile(r"{#(.*?)#}", re.DOTALL)
        return pattern.sub("", template)


    def _parse_unless(self):
        pass

    @staticmethod
    def _handle_csr(match, context):
        directive = match.group("directive")
        expression = match.group("expression")
        if not (eval(expression, {}, context)):
            return ""
        return directive

    def _parse_component(self):
        pass

    def _parse_match(self):
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
            count = int(context.get(count_var.strip(), 0)) if count_var else None

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
