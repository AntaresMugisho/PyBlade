import importlib
from pathlib import Path
import random
import re
from html import escape as html_escape
from pprint import pformat, pprint

from questionary.prompts.path import path

from pyblade.config import settings
from pyblade.engine.exceptions import (
    BreakLoopError,
    ComponentNotFoundError,
    ContinueLoopError,
    DirectiveParsingError,
    PyBladeException,
    TemplateNotFoundError,
    TemplateRenderError,
)
from pyblade.i18n import gettext, ngettext, npgettext, pgettext
from pyblade.utils import validate_single_root_node, snakebab_to_pascal, pascal_to_snake

from . import loader
from .contexts import AttributesContext, CycleContext, LoopContext
from .sandbox import SafeEvaluator


class Node:
    """Base class for all Abstract Syntax Tree nodes."""

    _evaluator = SafeEvaluator()

    _loop_control_help_message = "@break or @continue must be inside a @for loop. \
        Ensure this directive is not placed outside \
        or in a block that isn’t executed within a loop."

    _quick_fix_messages = {
        "AttributeError": "The object does not have the attribute "
        "you are trying to access. Make sure it is spelled correctly.",
        "SyntaxError": "There is a syntax error in your expression. "
        "Check your template syntax near the reported line.",
        "NameError": "The variable is not available in the current template context. "
        "Verify its spelling or use the @debug directive to inspect the context.",
        "TypeError": "An operation is being applied to an incompatible type.",
        "KeyError": "The key you are trying to access does not exist in the dictionary. "
        "Make sure it is spelled correctly. ",
        "PermissionError": "The operation you are trying to perform is not allowed in templates."
        "Review our security rules before retrying.",
        "ContinueLoopError": _loop_control_help_message,
        "BreakLoopError": _loop_control_help_message,
        "NoReverseMatch": "The URL could not be reversed. This usually means either the route \
            name is incorrect or some required parameters are missing. Double-check the URL name \
            and ensure all expected arguments are provided.",
    }

    _loop_control_error_message = "Loop control statement used outside of a loop"

    def __init__(self, line=None, column=None):
        self.line = line
        self.column = column

    def eval(self, expression, context):
        """Evaluate a Python-like expression string within the given context."""
        return self._evaluator.evaluate(expression, context)

    def render(self, context):
        """Render this node to a string using the provided context."""
        raise NotImplementedError

    def _raise(self, exc):
        """Raise a customized exception"""
        exc_name = exc.__class__.__name__
        help_message = self._quick_fix_messages.get(exc_name, "")
        raise TemplateRenderError(f"{exc_name}: {exc}", line=self.line, column=self.column, help=help_message)


# TEXT
class TextNode(Node):
    """Represents plain text content in the template."""

    def __init__(self, content, line=None, column=None):
        super().__init__(line, column)
        self.content = content

    def __repr__(self):
        return f"TextNode(content='{repr(self.content)}')"

    def render(self, context):
        return self.content


# VARIABLE
class VarNode(Node):
    """Represents a variable display block (e.g., {{ user.name }})."""

    def __init__(self, expression, escaped=True, line=None, column=None):
        super().__init__(line, column)
        self.expression = expression  # The Python expression string
        self.escaped = escaped  # Whether to HTML-escape the output

    def __repr__(self):
        escape_str = "escaped" if self.escaped else "unescaped"
        return f"VarNode(expression='{self.expression}', {escape_str})"

    def render(self, context):
        try:
            value = self.eval(self.expression, context)

        except Exception as exc:
            self._raise(exc)

        if value is None:
            rendered = ""
        else:
            rendered = str(value)

        return html_escape(rendered) if self.escaped else rendered


# DIRECTIVES
# ------------------------------------------------------------------------------------------------------------------------


class IfNode(Node):
    """Represents an @if...@elif...@else...@endif conditional block."""

    def __init__(self, condition, body, elif_blocks=None, else_body=None, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition  # The Python expression for the if condition
        self.body = body  # List of nodes in the main @if block
        self.elif_blocks = elif_blocks if elif_blocks is not None else []  # List of (condition_expr, body_nodes) tuples
        self.else_body = else_body  # List of nodes in the @else block

    def __repr__(self):
        elif_repr = ", ".join([f"(cond='{c}', body={b})" for c, b in self.elif_blocks])
        return (
            f"IfNode(\n"
            f"  condition='{self.condition}',\n"
            f"  body={self.body},\n"
            f"  elif_blocks=[{elif_repr}],\n"
            f"  else_body={self.else_body}\n"
            f")"
        )

    def render(self, context):
        try:
            if self.eval(self.condition, context):
                return "".join(node.render(context) for node in self.body)

            for cond_expr, body_nodes in self.elif_blocks:
                if self.eval(cond_expr, context):
                    return "".join(node.render(context) for node in body_nodes)

            if self.else_body is not None:
                return "".join(node.render(context) for node in self.else_body)

            return ""

        except (BreakLoopError, ContinueLoopError) as exc:
            raise exc

        except Exception as exc:
            self._raise(exc)


class UnlessNode(Node):
    """Represents an @unless...@endunless block."""

    def __init__(self, condition, body, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"UnlessNode(condition='{self.condition}', body={self.body})"

    def render(self, context):
        condition_result = self.eval(self.condition, context)
        if not condition_result:
            return "".join(node.render(context) for node in self.body)
        return ""


class SwitchNode(Node):
    """Represents an @switch...@endswitch block"""

    def __init__(self, expression, cases, default_body=None, line=None, column=None):
        super().__init__(line, column)
        self.expression = expression
        self.cases = cases  # List of (value_expr, body_nodes) tuples
        self.default_body = default_body

    def __repr__(self):
        cases_repr = ", ".join([f"(val='{v}', body={b})" for v, b in self.cases])
        return (
            f"SwitchNode(\n"
            f"  expression='{self.expression}',\n"
            f"  cases=[{cases_repr}],\n"
            f"  default_body={self.default_body}\n"
            f")"
        )

    def render(self, context):
        switch_value = self.eval(self.expression, context)

        for case_expr, body in self.cases:
            case_value = self.eval(case_expr, context)
            if case_value == switch_value:
                return "".join(node.render(context) for node in body)

        if self.default_body is not None:
            return "".join(node.render(context) for node in self.default_body)
        return ""


class AuthNode(Node):
    """Represents an @auth...@endauth block."""

    def __init__(self, body, else_body=None, guard=None, line=None, column=None):
        super().__init__(line, column)
        self.body = body
        self.else_body = else_body
        self.guard = guard

    def __repr__(self):
        return f"AuthNode(body={self.body}, else_body={self.else_body}, guard='{self.guard}')"

    def render(self, context):
        """Render content for authenticated users."""
        user = context.get("user")
        request = context.get("request")

        is_authenticated = False
        if user is not None:
            is_authenticated = getattr(user, "is_authenticated", False)
            if callable(is_authenticated):
                is_authenticated = is_authenticated()
        elif request is not None:
            user = getattr(request, "user", None)
            if user is not None:
                is_authenticated = getattr(user, "is_authenticated", False)
                if callable(is_authenticated):
                    is_authenticated = is_authenticated()

        if is_authenticated:
            return "".join(node.render(context) for node in self.body)
        if self.else_body:
            return "".join(node.render(context) for node in self.else_body)
        return ""


class GuestNode(Node):
    """Represents an @guest...@endguest block."""

    def __init__(self, body, else_body=None, guard=None, line=None, column=None):
        super().__init__(line, column)
        self.body = body
        self.else_body = else_body
        self.guard = guard

    def __repr__(self):
        return f"GuestNode(body={self.body}, else_body={self.else_body}, guard='{self.guard}')"

    def render(self, context):
        """Render content for guests (unauthenticated users), mirroring TemplateProcessor.render_guest."""
        user = context.get("user")
        request = context.get("request")

        is_authenticated = False
        if user is not None:
            is_authenticated = getattr(user, "is_authenticated", False)
            if callable(is_authenticated):
                is_authenticated = is_authenticated()
        elif request is not None:
            user = getattr(request, "user", None)
            if user is not None:
                is_authenticated = getattr(user, "is_authenticated", False)
                if callable(is_authenticated):
                    is_authenticated = is_authenticated()

        if not is_authenticated:
            return "".join(node.render(context) for node in self.body)
        if self.else_body:
            return "".join(node.render(context) for node in self.else_body)
        return ""


class ForNode(Node):
    """Represents an @for...@empty...@endfor loop block."""

    def __init__(self, item_var, collection_expr, body, empty_body=None, line=None, column=None):
        super().__init__(line, column)
        self.item_var = item_var  # The variable name for each item (e.g., 'fruit' in 'for fruit in fruits')
        self.collection_expr = collection_expr  # The Python expression for the iterable collection
        self.body = body  # List of nodes in the main @for loop block
        self.empty_body = empty_body  # List of nodes in the @empty block

    def __repr__(self):
        return (
            f"ForNode(\n"
            f"  item_var='{self.item_var}',\n"
            f"  collection_expr='{self.collection_expr}',\n"
            f"  body={self.body},\n"
            f"  empty_body={self.empty_body}\n"
            f")"
        )

    def render(self, context):
        iterable = self.eval(self.collection_expr, context)

        if not iterable:
            if self.empty_body is not None:
                return "".join(node.render(context) for node in self.empty_body)
            return ""

        # Make a shallow copy of context for loop modifications
        local_context = dict(context)
        output_parts = []

        current_loop = local_context.get("loop")
        loop = LoopContext(iterable, parent=current_loop)

        for index, item in enumerate(iterable):
            local_context[self.item_var] = item
            loop.index = index
            local_context["loop"] = loop

            try:
                for node in self.body:
                    output_parts.append(node.render(local_context))
            except BreakLoopError:
                break

            except ContinueLoopError:
                continue

        return "".join(output_parts)


class BreakNode(Node):
    """Represents an @break(condition) directive."""

    def __init__(self, condition=None, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition

    def __repr__(self):
        return f"BreakNode(condition='{self.condition}')"

    def render(self, context):
        """Signal a loop break when the optional condition is met."""
        if self.condition:
            if self.eval(self.condition, context):
                raise BreakLoopError(
                    message=self._loop_control_error_message,
                    line=self.line,
                    column=self.column,
                    help=self._quick_fix_messages["BreakLoopError"],
                )
        else:
            raise BreakLoopError(
                message=self._loop_control_error_message,
                line=self.line,
                column=self.column,
                help=self._quick_fix_messages["BreakLoopError"],
            )
        return ""


class ContinueNode(Node):
    """Represents an @continue(condition) directive."""

    def __init__(self, condition=None, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition

    def __repr__(self):
        return f"ContinueNode(condition='{self.condition}')"

    def render(self, context):
        """Signal a loop continue when the optional condition is met."""

        if self.condition:
            if self.eval(self.condition, context):
                raise ContinueLoopError(
                    message=self._loop_control_error_message,
                    line=self.line,
                    column=self.column,
                    help=self._quick_fix_messages["ContinueLoopError"],
                )
        else:
            raise ContinueLoopError(
                message=self._loop_control_error_message,
                line=self.line,
                column=self.column,
                help=self._quick_fix_messages["ContinueLoopError"],
            )

        return ""


class IncludeNode(Node):
    """Represents an @include('path') or @include('path', {'data': value}) directive."""

    def __init__(self, path_expr, data_expr=None, line=None, column=None):
        super().__init__(line, column)
        self.path_expr = path_expr
        self.data_expr = data_expr

    def __repr__(self):
        return f"IncludeNode(path_expr='{self.path_expr}', data_expr='{self.data_expr}')"

    def render(self, context):
        """Render an included template.

        Evaluates the path and optional data expression, then delegates to
        the loader to render the included template with a merged context.
        """
        try:
            # Evaluate the path expression
            path = self.eval(self.path_expr, context)

            # Evaluate data expression if provided
            data = {}
            if self.data_expr:
                data = self.eval(self.data_expr, context)
                if not isinstance(data, dict):
                    data = {}

            template = loader.load_template(path)

            # Create new context with additional data
            new_context = dict(context)
            new_context.update(data)

            return template.render(new_context)

        except TemplateNotFoundError as exc:
            setattr(exc, "line", self.line)
            setattr(exc, "column", self.column)
            raise

        except PyBladeException as exc:
            setattr(exc, "template", template)
            raise

        except Exception as exc:
            self._raise(exc)


class ExtendsNode(Node):
    """Represents an @extends('layout') directive."""

    def __init__(self, layout, line=None, column=None):
        super().__init__(line, column)
        self.layout = layout

    def __repr__(self):
        return f"ExtendsNode(layout='{self.layout}')"

    def render(self, context):
        """Mark the layout this template extends.

        Stores the evaluated layout path in the special '__extends' key in
        the rendering context. Actual inheritance resolution is handled by
        the loader/framework layer.
        """
        layout_path = self.eval(self.layout, context)
        context["__extends"] = layout_path
        return ""


class SectionNode(Node):
    """Represents an @section('name')...@endsection block (Laravel Blade style)."""

    def __init__(self, name, body, line=None, column=None):
        super().__init__(line, column)
        self.name = name
        self.body = body

    def __repr__(self):
        return f"SectionNode(name='{self.name}', body={self.body})"

    def render(self, context):
        """Render and register a named section.

        Renders the body to a string and stores it in context['__sections']
        under the evaluated section name, mirroring
        TemplateProcessor.render_section.
        """
        output = []
        for node in self.body:
            rendered = node.render(context)
            if rendered:
                output.append(rendered)
        content = "".join(output)

        name = self.eval(self.name, context)
        sections = context.setdefault("__sections", {})
        sections[name] = content

        return ""


class BlockNode(Node):
    """Represents a @block('name')...@endblock block (Django style)."""

    def __init__(self, name, body):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"BlockNode(name='{self.name}', body={self.body})"

    def render(self, context):
        """Render a block with optional override.

        If context['__blocks'][name] exists, it is returned; otherwise the
        block's own body is rendered. This matches the behavior relied on in
        test_block_inheritance.
        """
        # Resolve block name (usually a string literal)
        name = self.eval(self.name, context)

        # Check for override
        blocks = context.get("__blocks", {})
        if isinstance(blocks, dict) and name in blocks:
            return blocks[name]

        output = []
        for node in self.body:
            rendered = node.render(context)
            if rendered:
                output.append(rendered)
        return "".join(output)


class YieldNode(Node):
    """Represents an @yield('name', default) directive."""

    def __init__(self, name, default=None, line=None, column=None):
        super().__init__(line, column)
        self.name = name
        self.default = default

    def __repr__(self):
        return f"YieldNode(name='{self.name}', default='{self.default}')"

    def render(self, context):
        """Yield the content of a named section, with optional default.

        Mirrors TemplateProcessor.render_yield by looking up the evaluated
        name in context['__sections'] and falling back to the default
        expression when no section content is present.
        """
        name = self.eval(self.name, context)
        sections = context.get("__sections", {})
        content = sections.get(name)

        if content is None:
            if self.default:
                return self.eval(self.default, context)
            return ""
        return content


class AutoescapeNode(Node):
    """Represents an @autoescape(True/False)...@endautoescape block.

    This node is a structural hint that within its body, auto-escaping
    should be turned on or off. Because VarNode already controls escaping
    via its 'escaped' flag, and the current parser does not propagate a
    per-block escape state, the implementation here keeps behavior
    straightforward:

    - When enabled (True): simply render the body as-is; VarNode instances
      will escape according to how they were created by the parser.
    - When disabled (False): render the body but, for VarNode children,
      temporarily force 'escaped = False'.
    """

    def __init__(self, enabled, body, line=None, column=None):
        super().__init__(line, column)
        self.enabled = enabled
        self.body = body

    def __repr__(self):
        return f"AutoescapeNode(enabled={self.enabled}, body={self.body})"

    def render(self, context):
        # If autoescape is enabled, render body normally.
        if self.enabled:
            return "".join(node.render(context) for node in self.body)

        # If disabled, temporarily force VarNode instances to render unescaped.
        from .nodes import (
            VarNode as _VarNode,  # local import to avoid cycles in type hints
        )

        output = []
        for node in self.body:
            if isinstance(node, _VarNode):
                old_escaped = node.escaped
                try:
                    node.escaped = False
                    output.append(node.render(context))
                finally:
                    node.escaped = old_escaped
            else:
                output.append(node.render(context))

        return "".join(output)


class ComponentNode(Node):
    """Represents an @component('name', data)...@endcomponent block."""

    def __init__(self, path_expr, data_expr=None, line=None, column=None):
        super().__init__(line, column)
        self.path_expr = path_expr
        self.data_expr = data_expr

    def __repr__(self):
        return f"ComponentNode(path_expr='{self.path_expr}', data_expr='{self.data_expr}')"

    def _parse_props(self, component: str) -> tuple:
        """
        Parse the @props directive in the component
        """
        pattern = re.compile(r"@props\s*\((?P<dictionary>.*?)\s*\)", re.DOTALL)
        match = pattern.search(component)

        props = {}
        if match:
            component = re.sub(pattern, "", component)
            dictionary = match.group("dictionary")
            try:
                props = self.eval(dictionary, {})
            except (SyntaxError, ValueError) as e:
                raise e

        return component, props

    def _resolve_component(self, name: str):
        """
        Resolve a component.

        Static component:
            components/button.html

        Live component:
            components/counter/
                counter.py
                counter.html  # optional

        """
        name = pascal_to_snake(name)

        parts = name.replace(".", "/").split("/")
        component_name = parts[-1]
        components_dir = settings.components_dir
        parent = components_dir.joinpath(*parts[:-1])

        # Static component
        html_file = parent / f"{component_name}.html"
        if html_file.is_file():
            return {
                "type": "static",
                "html": html_file,
                "python": None,
            }

        # Single-file live component
        python_file = parent / f"{component_name}.py"
        if python_file.is_file():
            return {
                "type": "live",
                "html": None,
                "python": python_file,
            }

        # Directory-based live component
        directory = parent / component_name
        python_file = directory / f"{component_name}.py"
        html_file = directory / f"{component_name}.html"

        if python_file.is_file():
            return {
                "type": "live",
                "html": html_file if html_file.is_file() else None,
                "python": python_file,
            }

        return None

    def _render_static_component(self, name, data):

        template = loader.load_template(name, [settings.components_dir])
        original_content = template.content  # This is what may be displayed if an Exception occures

        if not validate_single_root_node(original_content):
            raise TemplateRenderError(
                "Component files should have single root node",
                help="Enclose all HTML tags into a single parent tag such as <div>...</div>",
                template=template,
                line=self.line,
            )

        new_content, props = self._parse_props(original_content)
        template.content = new_content

        data["attributes"] = AttributesContext(props=props, attributes={}, context=data)

        try:
            return template.render(props | data)
        except Exception:
            template.content = original_content
            raise

    def _render_live_component(self, python_file : Path, data):

        # Render the template content
        m = str(python_file.with_suffix("")).replace("/", ".")
        module_name = python_file.stem

        try:

            module = importlib.import_module(m) 
            cls = getattr(module, snakebab_to_pascal(module_name))

            template_name = getattr(cls, "template_name", ".".join(m.split(".")[1:]))
            setattr(cls, "template_name", template_name)
            template = cls.render_initial({}, {}, {}, "", None)
            return template
        except Exception:
            raise

    def render(self, context):
        """Render a component, similar to TemplateProcessor.render_component."""

        try:
            name = self.eval(self.path_expr, context)

            component = self._resolve_component(name)

            if component is None:
                raise ComponentNotFoundError(line=self.line, column=self.column, help="")

            data = {}
            if self.data_expr:
                data = self.eval(self.data_expr, context)
                if not isinstance(data, dict):
                    data = {}

            if component["type"] == "static":
                return self._render_static_component(name, data)

            elif component["type"] == "live":
                return self._render_live_component(component["python"], data)

        except TemplateRenderError:
            # To avoid the error being cathed by the following except clauses
            raise

        # except ComponentNotFoundError:
        #     raise

        # except TemplateNotFoundError as exc:
        #     setattr(exc, "line", self.line)
        #     setattr(exc, "column", self.column)
        #     raise

        # except PyBladeException as exc:
        #     setattr(exc, "template", template)
        #     raise

        except Exception as exc:
            self._raise(exc)


class SlotNode(Node):
    """Represents an @slot('name')...@endslot block."""

    def __init__(self, name, body):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"SlotNode(name='{self.name}', body={self.body})"

    def render(self, context):
        """Render and register a named slot in the context."""
        output = []
        for node in self.body:
            rendered = node.render(context)
            if rendered:
                output.append(rendered)
        content = "".join(output)

        name = self.eval(self.name, context)
        context[name] = content
        return ""


class VerbatimNode(Node):
    """Represents an @verbatim...@endverbatim block."""

    def __init__(self, content, line=None, column=None):
        super().__init__(line, column)
        self.content = content

    def __repr__(self):
        return f"VerbatimNode(content='{repr(self.content)}')"

    def render(self, context):
        return self.content


class CommentNode(Node):
    """Represents an @comment...@endcomment block."""

    def __init__(self, content, line=None, column=None):
        super().__init__(line, column)
        self.content = content

    def __repr__(self):
        return f"CommentNode(content='{repr(self.content)}')"

    def render(self, context):
        # Comments are stripped from output
        return ""


class CycleNode(Node):
    """Represents an @cycle(values) directive like Django's cycle tag."""

    def __init__(self, values, as_name=None, silent=False, line=None, column=None):
        super().__init__(line, column)
        self.values = values
        self.as_name = as_name
        self.silent = silent

    def __repr__(self):
        return f"CycleNode(values='{self.values}', as_name='{self.as_name}', silent={self.silent})"

    def render(self, context):
        cycles = context.setdefault("_cycles", {})

        # Check if it's a reference to a previously created cycle: @cycle(rowcolors)
        if self.values and not self.as_name and "," not in self.values:
            var_name = self.values.strip()
            # It could be an existing cycle renderer in the context or in _cycles
            if var_name in context and isinstance(context[var_name], CycleContext):
                if self.silent:
                    return ""
                return str(context[var_name])
            elif var_name in cycles:
                if self.silent:
                    return ""
                return str(cycles[var_name])

        # Evaluate the values
        values_evaluated = self.eval(f"({self.values})", context)
        if not isinstance(values_evaluated, (list, tuple)):
            values_evaluated = [values_evaluated]

        renderer = CycleContext(values_evaluated)

        if self.as_name:
            if self.as_name not in cycles:
                cycles[self.as_name] = renderer
                context[self.as_name] = renderer
            else:
                renderer = cycles[self.as_name]
                context[self.as_name] = renderer
        else:
            # Nameless cycle, tie its state to the node id
            cycle_id = f"cycle_node_{id(self)}"
            if cycle_id not in cycles:
                cycles[cycle_id] = renderer
            else:
                renderer = cycles[cycle_id]

        if self.silent:
            return ""
        return str(renderer)


class ResetCycleNode(Node):
    """Represents an @resetcycle(name) directive."""

    def __init__(self, name, line=None, column=None):
        super().__init__(line, column)
        self.name = name

    def __repr__(self):
        return f"ResetCycleNode(name='{self.name}')"

    def render(self, context):
        cycles = context.get("_cycles", {})
        name = self.name.strip()
        if name in cycles:
            cycles[name].reset()
        elif name in context and isinstance(context[name], CycleContext):
            context[name].reset()
        return ""


class FirstOfNode(Node):
    """Represents an @firstof(values, default) directive."""

    def __init__(self, values, default=None, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.values = values  # List of expressions
        self.default = default
        self.as_name = as_name

    def __repr__(self):
        return f"FirstOfNode(values={self.values}, default='{self.default}', as_name='{self.as_name}')"

    def render(self, context):
        """Return the first truthy value from the argument list, or default."""
        args = self.eval(f"({self.values})", context)
        if not isinstance(args, tuple):
            args = (args,)

        result = ""
        for arg in args:
            if arg:
                result = str(arg)
                break
        else:
            if self.default is not None:
                default_val = self.eval(self.default, context)
                if default_val is not None:
                    result = str(default_val)

        if self.as_name:
            context[self.as_name] = result
            return ""
        return html_escape(result)


class UrlNode(Node):
    """Represents an @url('pattern', args, kwargs) directive."""

    def __init__(self, pattern_expr, positional_args=None, keyword_args=None, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.pattern_expr = pattern_expr
        self.positional_args = positional_args or []
        self.keyword_args = keyword_args or {}
        self.as_name = as_name

    def __repr__(self):
        return f"UrlNode(pattern_expr='{self.pattern_expr}', \
        positional_args={self.positional_args}, keyword_args={self.keyword_args}, as_name='{self.as_name}')"

    def render(self, context):
        """Resolve a Django URL pattern with the new argument structure.

        Evaluates positional and keyword arguments separately and passes them
        to Django's reverse() function.
        """

        # Evaluate the URL pattern
        try:
            url_pattern = self.eval(self.pattern_expr, context)
        except Exception:
            url_pattern = None

        if not isinstance(url_pattern, str):
            url_pattern = str(url_pattern)

        url_pattern = context.get(url_pattern, url_pattern)

        # Evaluate positional arguments
        evaluated_positional = []
        for arg_expr in self.positional_args:
            try:
                evaluated = self.eval(arg_expr, context)
            except Exception:
                evaluated = arg_expr
            evaluated_positional.append(evaluated)

        # Evaluate keyword arguments
        evaluated_keyword = {}
        for key, value_expr in self.keyword_args.items():
            try:
                evaluated = self.eval(value_expr, context)
            except Exception:
                evaluated = value_expr
            evaluated_keyword[key] = evaluated

        try:
            from django.urls import reverse
        except ImportError:
            return ""

        try:
            url = reverse(
                url_pattern,
                args=evaluated_positional,
                kwargs=evaluated_keyword,
            )
        except Exception as exc:
            self._raise(exc)

        if self.as_name:
            context[self.as_name] = url
            return ""
        return url


class StaticNode(Node):
    """Represents an @static('path') directive."""

    def __init__(self, path, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.path = path
        self.as_name = as_name

    def __repr__(self):
        return f"StaticNode(path='{self.path}', as_name='{self.as_name}')"

    def render(self, context):
        try:
            path = self.eval(self.path, context)
        except Exception as exc:
            self._raise(exc)

        if settings.framework == "django":
            try:
                from django.conf import settings as dj_settings

                result = f"{dj_settings.STATIC_URL}{path}"
            except Exception as exc:
                self._raise(exc)
        else:
            result = f"/static/{path}"

        # If 'as variable_name' was specified, store the result in context
        if self.as_name:
            context[self.as_name] = result
            return ""  # Don't output anything when storing to variable
        else:
            return result


class CsrfNode(Node):
    """Represents an @csrf directive."""

    def __repr__(self):
        return "CsrfNode()"

    def render(self, context):
        token = context.get("csrf_token", "")
        return f'<input type="hidden" name="csrfmiddlewaretoken" value="{token}">'


class MethodNode(Node):
    """Represents an @method('POST') directive."""

    def __init__(self, method, line=None, column=None):
        super().__init__(line, column)
        self.method = method

    def __repr__(self):
        return f"MethodNode(method='{self.method}')"

    def render(self, context):
        method = self.eval(self.method, context)
        return f'<input type="hidden" name="_method" value="{method}">'


class StyleNode(Node):
    """Represents an @style directive with parsed positional and conditional values."""

    def __init__(self, positional_styles=None, conditional_expressions=None, line=None, column=None):
        super().__init__(line, column)
        self.positional_styles = positional_styles or []
        self.conditional_expressions = conditional_expressions or {}

    def __repr__(self):
        return f"StyleNode(positional={self.positional_styles}, conditional={self.conditional_expressions})"

    def render(self, context):
        # Start with positional styles
        style_list = list(self.positional_styles)

        # Evaluate conditional expressions and include truthy ones
        for style_name, expression in self.conditional_expressions.items():
            try:
                value = self.eval(expression, context)
                if value:
                    style_list.append(style_name)
            except Exception:
                pass

        # Remove duplicates while preserving order
        seen = set()
        unique_styles = []
        for style in style_list:
            if style not in seen:
                seen.add(style)
                unique_styles.append(style)

        if unique_styles:
            return f' style="{"; ".join(unique_styles)}"'

        return ""


class ClassNode(Node):
    """Represents an @class directive with parsed positional and conditional values."""

    def __init__(self, positional_classes=None, conditional_expressions=None, line=None, column=None):
        super().__init__(line, column)
        self.positional_classes = positional_classes or []
        self.conditional_expressions = conditional_expressions or {}

    def __repr__(self):
        return f"ClassNode(positional={self.positional_classes}, conditional={self.conditional_expressions})"

    def render(self, context):
        # Start with positional classes
        class_list = list(self.positional_classes)

        # Evaluate conditional expressions and include truthy ones
        for class_name, expression in self.conditional_expressions.items():

            try:
                value = self.eval(expression, context)
                if value:
                    class_list.append(class_name)
            except Exception:
                pass

        # Remove duplicates while preserving order
        seen = set()
        unique_classes = []
        for cls in class_list:
            if cls not in seen:
                seen.add(cls)
                unique_classes.append(cls)

        if unique_classes:
            return f' class="{" ".join(unique_classes)}"'

        return ""


class TranslateNode(Node):
    """Represents a @trans('message') directive."""

    def __init__(self, message, context=None, noop=False, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.message = message
        self.context = context
        self.noop = noop
        self.as_name = as_name

    def __repr__(self):
        return f"TranslateNode(message='{self.message}', context='{self.context}',"
        f" noop={self.noop}, as_name='{self.as_name}')"

    def render(self, context):
        """Render a translated string using standard gettext.

        Framework-agnostic implementation that uses Python's gettext module.
        Falls back to Django's i18n when available for compatibility.
        """

        args_str = self.message.strip()
        if args_str.startswith("(") and args_str.endswith(")"):
            args_str = args_str[1:-1]

        def _extract(*args, **kwargs):
            return args, kwargs

        eval_context = dict(context)
        eval_context["_extract"] = _extract

        # Try to evaluate the arguments
        try:
            extracted_args, extracted_kwargs = self.eval(f"_extract({args_str})", eval_context)

            if not extracted_args:
                raise ValueError("@trans requires a message")

            message = extracted_args[0]

            # If the message is not a string, try to convert it
            if not isinstance(message, str):
                message = str(message)

        except Exception:
            # If evaluation fails, try to use the raw message string
            # This handles cases where the message is a variable name
            message = args_str.strip()
            # Remove quotes if present
            if (message.startswith("'") and message.endswith("'")) or (
                message.startswith('"') and message.endswith('"')
            ):
                message = message[1:-1]
            else:
                # It might be a variable, try to evaluate it
                try:
                    message = self.eval(message, context)
                    if not isinstance(message, str):
                        message = str(message)
                except Exception:
                    message = str(message)

            extracted_kwargs = {}

        msg_context = extracted_kwargs.get("context") or self.context
        noop = extracted_kwargs.get("noop", False) or self.noop
        as_variable = extracted_kwargs.get("as") or self.as_name

        if noop:
            translated = message
        else:
            if msg_context:
                if not isinstance(msg_context, str):
                    raise TypeError("context must be a string")
                translated = pgettext(msg_context, message)
            else:
                translated = gettext(message)

        if as_variable:
            context[as_variable] = translated
            return ""

        return translated


class BlockTranslateNode(Node):
    """Represents an @blocktranslate...@plural...@endblocktranslate block."""

    def __init__(
        self, body, plural_body=None, count=None, context=None, trimmed=False, kwargs=None, line=None, column=None
    ):
        super().__init__(line, column)
        self.body = body
        self.plural_body = plural_body
        self.count = count
        self.context = context
        self.trimmed = trimmed
        self.kwargs = kwargs or {}

    def __repr__(self):
        return f"BlockTranslateNode(body={self.body}, \
        plural_body={self.plural_body}, \
        count='{self.count}', \
        context='{self.context}', \
        trimmed={self.trimmed}, \
        kwargs={self.kwargs})"

    def render(self, context):
        """Render a block translation with pluralization support.

        Converts {{ variable }} placeholders to %(variable)s for gettext,
        then translates using ngettext for plural forms.
        """
        # Evaluate kwargs and add to context
        eval_context = context.copy()
        for key, value_expr in self.kwargs.items():
            try:
                eval_context[key] = self.eval(value_expr, context)
            except Exception:
                eval_context[key] = ""

        # Evaluate count and add to context if it exists
        if self.count:
            try:
                count_value = self.eval(self.count, context)
                eval_context["count"] = count_value
            except Exception:
                eval_context["count"] = 1

        # Render the body to get the template string
        body_parts = []
        for node in self.body:
            rendered = node.render(eval_context)
            if rendered:
                body_parts.append(rendered)
        singular = "".join(body_parts)

        # Normalize whitespace if trimmed
        if self.trimmed:
            singular = " ".join(singular.split())

        # Convert {{ variable }} placeholders to %(variable)s
        placeholder_pattern = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
        singular = placeholder_pattern.sub(r"%(\1)s", singular)

        # Handle plural form
        if self.plural_body:
            plural_parts = []
            for node in self.plural_body:
                rendered = node.render(eval_context)
                if rendered:
                    plural_parts.append(rendered)
            plural = "".join(plural_parts)

            if self.trimmed:
                plural = " ".join(plural.split())

            # Convert placeholders in plural form
            plural = placeholder_pattern.sub(r"%(\1)s", plural)

            # Evaluate count expression
            count_value = 1
            if self.count:
                try:
                    count_value = self.eval(self.count, context)
                    if not isinstance(count_value, (int, float)):
                        count_value = 1
                except Exception:
                    count_value = 1

            # Build interpolation dict from eval_context
            # Extract all placeholder names from the template
            placeholders = placeholder_pattern.findall(singular)
            interp_dict = {}
            for placeholder in placeholders:
                if placeholder in eval_context:
                    interp_dict[placeholder] = eval_context[placeholder]

            # Translate with pluralization
            if self.context:
                translated = npgettext(self.context, singular, plural, count_value)
            else:
                translated = ngettext(singular, plural, count_value)

            # Interpolate placeholders
            try:
                result = translated % interp_dict
            except (KeyError, TypeError):
                # If interpolation fails, return the translated string as-is
                result = translated

            return result
        else:
            # Build interpolation dict from eval_context
            placeholders = placeholder_pattern.findall(singular)
            interp_dict = {}
            for placeholder in placeholders:
                if placeholder in eval_context:
                    interp_dict[placeholder] = eval_context[placeholder]

            # Translate
            if self.context:
                translated = pgettext(self.context, singular)
            else:
                translated = gettext(singular)

            # Interpolate placeholders
            try:
                result = translated % interp_dict
            except (KeyError, TypeError):
                result = translated

            return result


class WithNode(Node):
    """Represents a @with(vars)...@endwith block."""

    def __init__(self, variables, body, line=None, column=None):
        super().__init__(line, column)
        self.variables = variables  # Dictionary of {var_name: expression}
        self.body = body

    def __repr__(self):
        return f"WithNode(variables={self.variables}, body={self.body})"

    def render(self, context):
        """Render body with a temporary extended context.

        Expects variables to be a dictionary of {var_name: expression} as
        produced by the parser for better performance.
        """

        # Evaluate each variable expression and build the context
        vars_dict = {}
        for var_name, var_expr in self.variables.items():
            try:
                vars_dict[var_name] = self.eval(var_expr, context)
            except Exception as exc:
                self._raise(exc)

        new_context = dict(context)
        new_context.update(vars_dict)

        output = []
        for node in self.body:
            output.append(node.render(new_context))

        return "".join(output)


class NowNode(Node):
    """Represents a @now('format') directive."""

    def __init__(self, format_string, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.format_string = format_string
        self.as_name = as_name

    def __repr__(self):
        return f"NowNode(format_string='{self.format_string}', as_name='{self.as_name}')"

    def render(self, context):
        from datetime import datetime

        fmt = self.eval(self.format_string, context) or "%Y-%m-%d %H:%M:%S"
        result = datetime.now().strftime(fmt)
        if self.as_name:
            context[self.as_name] = result
            return ""
        return result


class RegroupNode(Node):
    """Represents a @regroup(target, by, as_name) directive."""

    def __init__(self, target, by, as_name, line=None, column=None):
        super().__init__(line, column)
        self.target = target
        self.by = by
        self.as_name = as_name

    def __repr__(self):
        return f"RegroupNode(target='{self.target}', by='{self.by}', as_name='{self.as_name}')"

    def render(self, context):
        """Regroup a list of dicts by a key, Django-style.

        Populates context[as_name] with a list of objects that have
        `.grouper` and `.list` attributes, similar to Django's regroup.
        """
        # Evaluate target
        try:
            target = self.eval(self.target, context)
        except Exception as exc:
            self._raise(exc)

        # by is treated as a literal attribute name, e.g. "country"
        by = self.by.strip()
        if by.startswith(("'", '"')) and by.endswith(("'", '"')):
            by = by[1:-1]

        if not target:
            context[self.as_name] = []
            return ""

        from collections import defaultdict

        groups = defaultdict(list)
        for item in target:
            key = item.get(by) if isinstance(item, dict) else getattr(item, by, None)
            groups[key].append(item)

        class Group:
            def __init__(self, grouper, items):
                self.grouper = grouper
                self.list = items

        result = [Group(k, v) for k, v in groups.items()]
        context[self.as_name] = result
        return ""


class DebugNode(Node):
    """Represents a @debug directive that dumps the current context."""

    def __repr__(self):
        return "DebugNode()"

    def render(self, context):
        """Render a pretty representation of the context dictionary if the app is in DEBUG Mode.
        We avoid including private/special keys
        """

        if not settings.DEBUG:
            return ""

        public_items = {k: v for k, v in sorted(context.items()) if not str(k).startswith("__")}
        pretty_repr = pformat(public_items, indent=4, width=120, depth=4)
        return f"<pre>{html_escape(pretty_repr)}</pre>"


class LoremNode(Node):
    """Represents a @lorem directive that outputs placeholder text.

    @lorem(1)              -> 1 paragraph
    @lorem(3, 'w')         -> 3 words
    @lorem(2, 'p', True)   -> 2 paragraphs with HTML <p> wrappers
    """

    _LOREM_WORDS = "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore \
         et dolore magna aliqua".split()

    def __init__(self, args_expr, line=None, column=None):
        super().__init__(line, column)
        self.args_expr = args_expr

    def __repr__(self):
        return f"LoremNode(args_expr='{self.args_expr}')"

    def render(self, context):
        # Default behavior: 1 paragraph, words ("w"), no HTML
        count = 1
        method = "b"  # Can be 'w' words, 'p' HTML paragraphs, 'b' plain-text paragraphs without any HTML Tag
        random_order = False

        def generate_words(count: int, random_order: bool = False) -> str:
            words = list(self._LOREM_WORDS)
            if random_order:
                random.shuffle(words)
            out_words = (words * ((count // len(words)) + 1))[:count]
            return " ".join(out_words)

        def generate_paragraphs(count: int, random_order: bool = False) -> str:
            paragraphs = []
            for _ in range(count):
                words = generate_words(random.randint(20, 100), random_order)
                paragraphs.append(words.capitalize() + ".")
            return paragraphs

        if self.args_expr:
            args = self.eval(f"({self.args_expr})", context)
            if not isinstance(args, tuple):
                args = (args,)

            if len(args) > 0 and args[0] is not None:
                try:
                    count = int(args[0])
                except (TypeError, ValueError):
                    pass
            if len(args) > 1 and args[1] is not None:
                method = str(args[1]).lower()
            if len(args) > 2 and args[2] is not None:
                random_order = bool(args[2])

        if method == "w":
            return generate_words(count, random_order)
        elif method == "b":
            return "\n\n".join(generate_paragraphs(count, random_order))
        elif method == "p":
            return "".join([f"<p>{p}</p>" for p in generate_paragraphs(count, random_order)])
        else:
            raise DirectiveParsingError(
                f"Invalid method name passed to @lorem directive: '{method}'."
                "\nSupported methods are 'w', 'b' and 'p'.",
                line=self.line,
                column=self.column,
            )


class SpacelessNode(Node):
    """Represents a @spaceless...@endspaceless block.

    Collapses whitespace between HTML tags.
    """

    _between_tags_re = re.compile(r">\s+<")

    def __init__(self, body):
        self.body = body

    def __repr__(self):
        return f"SpacelessNode(body={self.body})"

    def render(self, context):
        content = "".join(node.render(context) for node in self.body)
        # Strip leading/trailing whitespace and collapse between tags
        content = content.strip()
        return self._between_tags_re.sub("><", content)


class SelectedNode(Node):
    """Represents a @selected(condition) directive."""

    def __init__(self, condition, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition

    def __repr__(self):
        return f"SelectedNode(condition='{self.condition}')"

    def render(self, context):
        if self.eval(self.condition, context):
            return " selected"
        return ""


class RequiredNode(Node):
    """Represents a @required(condition) directive."""

    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"RequiredNode(condition='{self.condition}')"

    def render(self, context):
        if self.eval(self.condition, context):
            return " required"
        return ""


class CheckedNode(Node):
    """Represents a @checked(condition) directive."""

    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"CheckedNode(condition='{self.condition}')"

    def render(self, context):
        if self.eval(self.condition, context):
            return " checked"
        return ""


class AutocompleteNode(Node):
    """Represents a @autocomplete(value) directive."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"AutocompleteNode(value='{self.value}')"

    def render(self, context):
        value = self.eval(self.value, context) if isinstance(self.value, str) else self.value
        if value is None:
            return ""
        return f' autocomplete="{value}"'


class RatioNode(Node):
    """Represents a @ratio(w, h) directive."""

    def __init__(self, args_expr, as_name=None, line=None, column=None):
        super().__init__(line=line, column=column)
        self.args_expr = args_expr
        self.as_name = as_name

    def __repr__(self):
        return f"RatioNode(args_expr='{self.args_expr}', as_name='{self.as_name}')"

    def render(self, context):
        expr = self.args_expr.strip()
        if not expr:
            result = "0"
        else:
            # Expect three comma-separated expressions: value, max_value, max_width
            # We evaluate each part individually for clarity.
            parts = [p.strip() for p in expr.split(",") if p.strip()]
            if len(parts) != 3:
                raise DirectiveParsingError(
                    f"The @ratio directive expects 3 parametters but only {len(parts)} were provided",
                    line=self.line,
                    column=self.column,
                    help="Check the official PyBlade documentation for the right syntax of @ratio directive.",
                )

            val_expr, max_expr, width_expr = parts
            val = self.eval(val_expr, context) or 0
            max_val = self.eval(max_expr, context) or 0
            width = self.eval(width_expr, context) or 0

            try:
                if not max_val:
                    result = "0"
                else:
                    ratio = (float(val) / float(max_val)) * float(width)
                    result = str(int(round(ratio, 0)))
            except Exception:
                result = "0"

        # If 'as variable_name' was specified, store the result in context
        if self.as_name:
            context[self.as_name] = result
            return ""  # Don't output anything when storing to variable

        return result


class GetStaticPrefixNode(Node):
    """Represents a @get_static_prefix directive."""

    def __init__(self, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.as_name = as_name

    def __repr__(self):
        return f"GetStaticPrefixNode(as_name='{self.as_name}')"

    def render(self, context):
        try:
            from django.conf import settings as dj_settings

            result = dj_settings.STATIC_URL
        except Exception:
            # Fallback to a sensible default
            result = "/static/"

        # If 'as variable_name' was specified, store the result in context
        if self.as_name:
            context[self.as_name] = result
            return ""  # Don't output anything when storing to variable
        else:
            return result


class GetMediaPrefixNode(Node):
    """Represents a @get_media_prefix directive."""

    def __init__(self, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.as_name = as_name

    def __repr__(self):
        return f"GetMediaPrefixNode(as_name='{self.as_name}')"

    def render(self, context):
        try:
            from django.conf import settings as dj_settings

            result = dj_settings.MEDIA_URL
        except Exception:
            result = "/media/"

        # If 'as variable_name' was specified, store the result in context
        if self.as_name:
            context[self.as_name] = result
            return ""  # Don't output anything when storing to variable
        else:
            return result


class QuerystringNode(Node):
    """Represents a @querystring(kwargs) directive."""

    def __init__(self, kwargs_expr, as_name=None, line=None, column=None):
        super().__init__(line=line, column=column)
        self.kwargs_expr = kwargs_expr
        self.as_name = as_name

    def __repr__(self):
        return f"QuerystringNode(kwargs_expr='{self.kwargs_expr}', as_name='{self.as_name}')"

    def render(self, context):
        """Build a querystring based on request.GET and overrides.

        Mirrors TemplateProcessor.render_querystring using SafeEvaluator.
        """
        request = context.get("request")
        if request is None or not hasattr(request, "GET"):
            result = ""
        else:
            query_dict = request.GET.copy().dict()

            # kwargs_expr is like "page=2"; wrap it in dict(...) for evaluation
            expr = self.kwargs_expr.strip()
            if expr:
                try:
                    # Basic parsing for "page=2, sort=asc"
                    overrides = {}
                    for part in expr.split(","):
                        if "=" in part:
                            k, v = part.split("=", 1)
                            value = self.eval(v.strip(), context)
                            if value is None:
                                query_dict.pop(k.strip(), None)
                                continue

                            overrides[k.strip()] = value
                    query_dict.update(overrides)
                except Exception as exc:
                    self._raise(exc)

            from urllib.parse import urlencode

            result = "?" + urlencode(query_dict)

        # If 'as variable_name' was specified, store the result in context
        if self.as_name:
            context[self.as_name] = result
            return ""  # Don't output anything when storing to variable
        else:
            return result


class IfChangedNode(Node):
    """Represents an @ifchanged(args)...@else...@endifchanged block."""

    def __init__(self, check_expr, body, else_body=None, line=None, column=None):
        super().__init__(line, column)
        self.check_expr = check_expr
        self.body = body
        self.else_body = else_body

    def __repr__(self):
        return f"IfChangedNode(check_expr='{self.check_expr}', body={self.body}, else_body={self.else_body})"

    def render(self, context):
        if not hasattr(self, "_last_state"):
            self._last_state = None

        # If no arguments are provided, compare the rendered output of the body
        if not self.check_expr:
            rendered_body = "".join(node.render(context) for node in self.body)
            if self._last_state != rendered_body:
                self._last_state = rendered_body
                return rendered_body
            else:
                if self.else_body:
                    return "".join(node.render(context) for node in self.else_body)
                return ""
        else:
            try:
                current_values = self.eval(f"({self.check_expr})", context)
            except Exception as exc:
                self._raise(exc)

            if not isinstance(current_values, tuple):
                current_values = (current_values,)

            has_changed = self._last_state != current_values

            if has_changed:
                self._last_state = current_values
                return "".join(node.render(context) for node in self.body)
            else:
                if self.else_body:
                    return "".join(node.render(context) for node in self.else_body)
                return ""


class LiveBladeNode(Node):
    """Represents a @live directive."""

    def __repr__(self):
        return "LiveBladeNode()"

    def render(self, context):
        # Placeholder for future live-reload / interactive behavior.
        # Currently behaves as a no-op marker.
        return ""
