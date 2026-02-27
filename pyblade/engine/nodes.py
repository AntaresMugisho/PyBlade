import random
import re
from html import escape as html_escape
from pprint import pformat

from pyblade.config import settings
from pyblade.engine.exceptions import (  # TemplateNotFoundError,; UndefinedVariableError,
    DirectiveParsingError,
    TemplateRenderError,
)

from .sandbox import SafeEvaluator


class Node:
    """Base class for all Abstract Syntax Tree nodes."""

    _evaluator = SafeEvaluator()

    def __init__(self, line=None, column=None):
        self.line = line
        self.column = column

    def eval(self, expression, context):
        """Evaluate a Python-like expression string within the given context."""
        return self._evaluator.evaluate(expression, context)

    def render(self, context):
        """Render this node to a string using the provided context."""
        raise NotImplementedError


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
            raise TemplateRenderError(
                f"{exc.__class__.__name__}: {exc}",
                line=self.line,
            )
        if value is None:
            rendered = ""
        else:
            rendered = str(value)
        return html_escape(rendered) if self.escaped else rendered


# DIRECTIVES
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
        if self.eval(self.condition, context):
            return "".join(node.render(context) for node in self.body)

        for cond_expr, body_nodes in self.elif_blocks:
            if self.eval(cond_expr, context):
                return "".join(node.render(context) for node in body_nodes)

        if self.else_body is not None:
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

        for item in iterable:
            local_context[self.item_var] = item
            for node in self.body:
                output_parts.append(node.render(local_context))

        return "".join(output_parts)


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
        """Render content for authenticated users, mirroring TemplateProcessor.render_auth."""
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

    def __init__(self, body, else_body=None, guard=None):
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


class IncludeNode(Node):
    """Represents an @include('path', data) directive."""

    def __init__(self, path, data_expr=None, line=None, column=None):
        super().__init__(line, column)
        self.path = path
        self.data_expr = data_expr

    def __repr__(self):
        return f"IncludeNode(path='{self.path}', data_expr='{self.data_expr}')"

    def render(self, context):
        """Render an included template.

        Evaluates the include arguments to get (path, data) and delegates to
        the loader to render the included template with a merged context.
        Mirrors TemplateProcessor.render_include.
        """
        try:
            # path/data are passed as a raw args string, e.g. "'partials.header', {'a': 1}"
            args_tuple = self.eval(f"({self.path})", context)
            if not isinstance(args_tuple, tuple):
                args_tuple = (args_tuple,)

            path = args_tuple[0]
            data = args_tuple[1] if len(args_tuple) > 1 else {}

            from . import loader

            template = loader.load_template(path)

            new_context = dict(context)
            if isinstance(data, dict):
                new_context.update(data)

            return template.render(new_context)

        except Exception:
            # Propagate or log in higher layers; for now fail loudly to match prior behavior
            raise


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

    def __init__(self, name, data_expr=None, body=None, line=None, column=None):
        super().__init__(line, column)
        self.name = name
        self.data_expr = data_expr
        self.body = body  # The default slot content

    def __repr__(self):
        return f"ComponentNode(name='{self.name}', data_expr='{self.data_expr}', body={self.body})"

    def render(self, context):
        """Render a component, similar to TemplateProcessor.render_component."""
        try:
            args_tuple = self.eval(f"({self.name})", context)
            if not isinstance(args_tuple, tuple):
                args_tuple = (args_tuple,)

            name = args_tuple[0]
            data = args_tuple[1] if len(args_tuple) > 1 else {}

            from . import loader

            # Render body as default slot
            output = []
            if self.body:
                for node in self.body:
                    rendered = node.render(context)
                    if rendered:
                        output.append(rendered)
            slot_content = "".join(output)

            new_context = dict(context)
            if isinstance(data, dict):
                new_context.update(data)
            new_context["slot"] = slot_content

            path = f"components/{name}.html"
            template = loader.load_template(path)

            return template.render(new_context)

        except Exception as exc:
            return f"<!-- Error rendering component '{self.name}': {exc} -->"


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

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"CommentNode(content='{repr(self.content)}')"

    def render(self, context):
        # Comments are stripped from output
        return ""


class CycleNode(Node):
    """Represents an @cycle(values) directive."""

    def __init__(self, values, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.values = values  # List of expressions
        self.as_name = as_name

    def __repr__(self):
        return f"CycleNode(values={self.values}, as_name='{self.as_name}')"

    def render(self, context):
        """Cycle through values based on the current loop index.

        Mirrors TemplateProcessor.render_cycle behavior: evaluate the values
        tuple once, then select based on loop.index when available.
        """
        # values is an args string like "'odd', 'even'"
        values = self.eval(f"({self.values})", context)
        if not isinstance(values, (list, tuple)):
            values = [values]

        loop = context.get("loop")
        if loop is not None:
            index = getattr(loop, "index", 0)
            return str(values[index % len(values)])
        return str(values[0]) if values else ""


class FirstOfNode(Node):
    """Represents an @firstof(values, default) directive."""

    def __init__(self, values, default=None, line=None, column=None):
        super().__init__(line, column)
        self.values = values  # List of expressions
        self.default = default

    def __repr__(self):
        return f"FirstOfNode(values={self.values}, default='{self.default}')"

    def render(self, context):
        """Return the first truthy value from the argument list, or default."""
        args = self.eval(f"({self.values})", context)
        if not isinstance(args, tuple):
            args = (args,)

        for arg in args:
            if arg:
                return str(arg)

        if self.default is not None:
            default_val = self.eval(self.default, context)
            if default_val is not None:
                return str(default_val)
        return ""


class UrlNode(Node):
    """Represents an @url('name', params) directive."""

    def __init__(self, name, params_expr=None, as_name=None, line=None, column=None):
        super().__init__(line, column)
        self.name = name
        self.params_expr = params_expr
        self.as_name = as_name

    def __repr__(self):
        return f"UrlNode(name='{self.name}', params_expr='{self.params_expr}', as_name='{self.as_name}')"

    def render(self, context):
        """Resolve a Django URL pattern if possible.

        This is a simplified adaptation of directives._parse_url and
        TemplateProcessor.render_url. If Django is not available, returns
        an empty string.
        """
        pattern_expr = self.name
        params_expr = self.params_expr
        as_var = self.as_name

        try:
            # Resolve pattern: may be a literal or a variable name in context
            url_pattern = self.eval(pattern_expr, context)
        except Exception:
            url_pattern = None

        if not isinstance(url_pattern, str):
            url_pattern = str(url_pattern)

        url_pattern = context.get(url_pattern, url_pattern)

        url_params = []
        if params_expr:
            params_str = params_expr
            for param in params_str.split(","):
                param = param.strip()
                if not param:
                    continue
                if "=" in param:
                    key, value = param.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        evaluated = self.eval(value, context)
                    except Exception:
                        evaluated = value
                    url_params.append((key, evaluated))
                else:
                    try:
                        evaluated = self.eval(param, context)
                    except Exception:
                        evaluated = param
                    url_params.append(("", evaluated))

        try:
            from django.urls import reverse
        except ImportError:
            return ""

        url = reverse(
            url_pattern,
            args=[p[1] for p in url_params if not p[0]],
            kwargs={p[0]: p[1] for p in url_params if p[0]},
        )

        if as_var:
            context[as_var] = url
            return ""
        return url


class StaticNode(Node):
    """Represents an @static('path') directive."""

    def __init__(self, path, line=None, column=None):
        super().__init__(line, column)
        self.path = path

    def __repr__(self):
        return f"StaticNode(path='{self.path}')"

    def render(self, context):
        path = self.eval(self.path, context)
        return f"/static/{path}"


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
    """Represents an @style(dict) directive."""

    def __init__(self, expression, line=None, column=None):
        super().__init__(line, column)
        self.expression = expression

    def __repr__(self):
        return f"StyleNode(expression='{self.expression}')"

    def render(self, context):
        styles = self.eval(self.expression, context)
        if not isinstance(styles, dict):
            return ""

        parts = [key for key, value in styles.items() if value]
        if not parts:
            return ""
        return f' style="{"; ".join(parts)}"'


class ClassNode(Node):
    """Represents an @class(dict) directive."""

    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return f"ClassNode(expression='{self.expression}')"

    def render(self, context):
        classes = self.eval(self.expression, context)
        if isinstance(classes, dict):
            class_list = [k for k, v in classes.items() if v]
            if class_list:
                return f' class="{" ".join(class_list)}"'
        return ""


class BreakNode(Node):
    """Represents an @break(condition) directive."""

    def __init__(self, condition=None, line=None, column=None):
        super().__init__(line, column)
        self.condition = condition

    def __repr__(self):
        return f"BreakNode(condition='{self.condition}')"

    def render(self, context):
        """Signal a loop break when the optional condition is met."""
        from .exceptions import BreakLoop

        if self.condition:
            if self.eval(self.condition, context):
                raise BreakLoop()
        else:
            raise BreakLoop()
        return ""


class ContinueNode(Node):
    """Represents an @continue(condition) directive."""

    def __init__(self, condition=None):
        self.condition = condition

    def render(self, context):
        """Signal a loop continue when the optional condition is met."""
        from .exceptions import ContinueLoop

        if self.condition:
            if self.eval(self.condition, context):
                raise ContinueLoop()
        else:
            raise ContinueLoop()
        return ""


class TranslateNode(Node):
    """Represents a @trans('message') directive."""

    def __init__(self, message, context=None, noop=False, line=None, column=None):
        super().__init__(line, column)
        self.message = message
        self.context = context
        self.noop = noop

    def __repr__(self):
        return f"TranslateNode(message='{self.message}', context='{self.context}', noop={self.noop})"

    def render(self, context):
        """Render a translated string using Django's i18n utilities when available.

        Mirrors the behavior of TemplateProcessor.render_trans using the same
        argument parsing strategy but localized to this node.
        """
        import re as _re

        args_str = self.message.strip()
        if args_str.startswith("(") and args_str.endswith(")"):
            args_str = args_str[1:-1]

        as_variable = None
        as_match = _re.search(
            r"""
            ^
            \s*
            (?P<msg>['"].+?['"])
            \s+as\s+
            (?P<var>[a-zA-Z_][a-zA-Z0-9_]*)
            \s*$
            """,
            args_str,
            _re.VERBOSE,
        )

        if as_match:
            args_str = as_match.group("msg")
            as_variable = as_match.group("var")

        def _extract(*args, **kwargs):
            return args, kwargs

        eval_context = dict(context)
        eval_context["_extract"] = _extract

        extracted_args, extracted_kwargs = self.eval(f"_extract({args_str})", eval_context)

        if not extracted_args:
            raise ValueError("@trans requires a string literal")

        message = extracted_args[0]
        if not isinstance(message, str):
            raise TypeError("@trans message must be a string literal")

        msg_context = extracted_kwargs.get("context")
        noop = extracted_kwargs.get("noop", False)

        if noop:
            translated = message
        else:
            try:
                from django.utils.translation import gettext_lazy, pgettext
            except ImportError as exc:  # pragma: no cover - only when Django absent
                raise RuntimeError("Django is required to use @trans directive") from exc

            if msg_context:
                if not isinstance(msg_context, str):
                    raise TypeError("context must be a string")
                translated = pgettext(msg_context, message)
            else:
                translated = gettext_lazy(message)

        if as_variable:
            context[as_variable] = translated
            return ""

        return translated


class BlockTranslateNode(Node):
    """Represents an @blocktranslate...@plural...@endblocktranslate block."""

    def __init__(self, body, plural_body=None, count=None, context=None, trimmed=False, line=None, column=None):
        super().__init__(line, column)
        self.body = body
        self.plural_body = plural_body
        self.count = count
        self.context = context
        self.trimmed = trimmed

    def __repr__(self):
        return f"BlockTranslateNode(body={self.body}, \
        plural_body={self.plural_body}, \
        count='{self.count}', \
        context='{self.context}', \
        trimmed={self.trimmed}')"


class WithNode(Node):
    """Represents a @with(vars)...@endwith block."""

    def __init__(self, variables, body, line=None, column=None):
        super().__init__(line, column)
        self.variables = variables  # Dictionary or list of assignments
        self.body = body

    def __repr__(self):
        return f"WithNode(variables={self.variables}, body={self.body})"

    def render(self, context):
        """Render body with a temporary extended context.

        Expects variables to be an argument string such as "a=1, b=2" or
        "(a=1, b=2)" as produced by the parser, similar to the old
        TemplateProcessor.render_with implementation.
        """
        vars_str = self.variables.strip()
        if vars_str.startswith("(") and vars_str.endswith(")"):
            vars_str = vars_str[1:-1]

        # Evaluate using SafeEvaluator in the current context
        vars_dict = self.eval(f"dict({vars_str})", context)

        new_context = dict(context)
        new_context.update(vars_dict)

        output = []
        for node in self.body:
            output.append(node.render(new_context))

        return "".join(output)


class NowNode(Node):
    """Represents a @now('format') directive."""

    def __init__(self, format_string, line=None, column=None):
        super().__init__(line, column)
        self.format_string = format_string

    def __repr__(self):
        return f"NowNode(format_string='{self.format_string}')"

    def render(self, context):
        from datetime import datetime

        fmt = self.eval(self.format_string, context)
        return datetime.now().strftime(fmt)


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
        # Evaluate target and by expressions
        target = self.eval(self.target, context)
        by = self.eval(self.by, context)

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

    def __init__(self, args_expr):
        self.args_expr = args_expr

    def __repr__(self):
        return f"RatioNode(args_expr='{self.args_expr}')"

    def render(self, context):
        expr = self.args_expr.strip()
        if not expr:
            return "0"

        # Expect three comma-separated expressions: value, max_value, max_width
        # We evaluate each part individually for clarity.
        parts = [p.strip() for p in expr.split(",") if p.strip()]
        if len(parts) != 3:
            # Fallback: try to evaluate as a single expression
            value = self.eval(expr, context)
            return str(int(value)) if value is not None else "0"

        val_expr, max_expr, width_expr = parts
        val = self.eval(val_expr, context) or 0
        max_val = self.eval(max_expr, context) or 0
        width = self.eval(width_expr, context) or 0

        try:
            if not max_val:
                return "0"
            ratio = (float(val) / float(max_val)) * float(width)
            return str(int(ratio))
        except Exception:
            return "0"


class GetStaticPrefixNode(Node):
    """Represents a @get_static_prefix directive."""

    def __repr__(self):
        return "GetStaticPrefixNode()"

    def render(self, context):
        try:
            from django.conf import settings as dj_settings

            return dj_settings.STATIC_URL
        except Exception:
            # Fallback to a sensible default
            return "/static/"


class GetMediaPrefixNode(Node):
    """Represents a @get_media_prefix directive."""

    def __repr__(self):
        return "GetMediaPrefixNode()"

    def render(self, context):
        try:
            from django.conf import settings as dj_settings

            return dj_settings.MEDIA_URL
        except Exception:
            return "/media/"


class QuerystringNode(Node):
    """Represents a @querystring(kwargs) directive."""

    def __init__(self, kwargs_expr):
        self.kwargs_expr = kwargs_expr

    def __repr__(self):
        return f"QuerystringNode(kwargs_expr='{self.kwargs_expr}')"

    def render(self, context):
        """Build a querystring based on request.GET and overrides.

        Mirrors TemplateProcessor.render_querystring using SafeEvaluator.
        """
        request = context.get("request")
        if request is None or not hasattr(request, "GET"):
            return ""

        query_dict = request.GET.copy().dict()

        # kwargs_expr is like "page=2"; wrap it in dict(...) for evaluation
        expr = self.kwargs_expr.strip()
        if expr:
            overrides = self.eval(f"dict({expr})", context)
            if isinstance(overrides, dict):
                query_dict.update(overrides)

        from urllib.parse import urlencode

        return "?" + urlencode(query_dict)


class LiveBladeNode(Node):
    """Represents a @liveblade directive."""

    def __repr__(self):
        return "LiveBladeNode()"

    def render(self, context):
        # Placeholder for future live-reload / interactive behavior.
        # Currently behaves as a no-op marker.
        return ""
