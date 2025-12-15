class Node:
    """Base class for all Abstract Syntax Tree nodes."""

    pass


# TEXT
class TextNode(Node):
    """Represents plain text content in the template."""

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"TextNode(content='{repr(self.content)}')"


# VARIABLE
class VarNode(Node):
    """Represents a variable display block (e.g., {{ user.name }})."""

    def __init__(self, expression, escaped=True):
        self.expression = expression  # The Python expression string
        self.escaped = escaped  # Whether to HTML-escape the output

    def __repr__(self):
        escape_str = "escaped" if self.escaped else "unescaped"
        return f"VarNode(expression='{self.expression}', {escape_str})"


# DIRECTIVES
class IfNode(Node):
    """Represents an @if...@elif...@else...@endif conditional block."""

    def __init__(self, condition, body, elif_blocks=None, else_body=None):
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


class ForNode(Node):
    """Represents an @for...@empty...@endfor loop block."""

    def __init__(self, item_var, collection_expr, body, empty_body=None):
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


class UnlessNode(Node):
    """Represents an @unless...@endunless block."""

    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"UnlessNode(condition='{self.condition}', body={self.body})"


class SwitchNode(Node):
    """Represents an @switch...@endswitch block"""

    def __init__(self, expression, cases, default_body=None):
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


class AuthNode(Node):
    """Represents an @auth...@endauth block."""

    def __init__(self, body, else_body=None, guard=None):
        self.body = body
        self.else_body = else_body
        self.guard = guard

    def __repr__(self):
        return f"AuthNode(body={self.body}, else_body={self.else_body}, guard='{self.guard}')"


class GuestNode(Node):
    """Represents an @guest...@endguest block."""

    def __init__(self, body, else_body=None, guard=None):
        self.body = body
        self.else_body = else_body
        self.guard = guard

    def __repr__(self):
        return f"GuestNode(body={self.body}, else_body={self.else_body}, guard='{self.guard}')"


class IncludeNode(Node):
    """Represents an @include('path', data) directive."""

    def __init__(self, path, data_expr=None):
        self.path = path
        self.data_expr = data_expr

    def __repr__(self):
        return f"IncludeNode(path='{self.path}', data_expr='{self.data_expr}')"


class ExtendsNode(Node):
    """Represents an @extends('layout') directive."""

    def __init__(self, layout):
        self.layout = layout

    def __repr__(self):
        return f"ExtendsNode(layout='{self.layout}')"


class SectionNode(Node):
    """Represents an @section('name')...@endsection block."""

    def __init__(self, name, body):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"SectionNode(name='{self.name}', body={self.body})"


class YieldNode(Node):
    """Represents an @yield('name', default) directive."""

    def __init__(self, name, default=None):
        self.name = name
        self.default = default

    def __repr__(self):
        return f"YieldNode(name='{self.name}', default='{self.default}')"


class ComponentNode(Node):
    """Represents an @component('name', data)...@endcomponent block."""

    def __init__(self, name, data_expr=None, body=None):
        self.name = name
        self.data_expr = data_expr
        self.body = body  # The default slot content

    def __repr__(self):
        return f"ComponentNode(name='{self.name}', data_expr='{self.data_expr}', body={self.body})"


class SlotNode(Node):
    """Represents an @slot('name')...@endslot block."""

    def __init__(self, name, body):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"SlotNode(name='{self.name}', body={self.body})"


class VerbatimNode(Node):
    """Represents an @verbatim...@endverbatim block."""

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"VerbatimNode(content='{repr(self.content)}')"


class PythonNode(Node):
    """Represents an @python...@endpython block."""

    def __init__(self, code):
        self.code = code

    def __repr__(self):
        return f"PythonNode(code='{repr(self.code)}')"


class CommentNode(Node):
    """Represents an @comment...@endcomment block."""

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"CommentNode(content='{repr(self.content)}')"


class CycleNode(Node):
    """Represents an @cycle(values) directive."""

    def __init__(self, values, as_name=None):
        self.values = values  # List of expressions
        self.as_name = as_name

    def __repr__(self):
        return f"CycleNode(values={self.values}, as_name='{self.as_name}')"


class FirstOfNode(Node):
    """Represents an @firstof(values, default) directive."""

    def __init__(self, values, default=None):
        self.values = values  # List of expressions
        self.default = default

    def __repr__(self):
        return f"FirstOfNode(values={self.values}, default='{self.default}')"


class UrlNode(Node):
    """Represents an @url('name', params) directive."""

    def __init__(self, name, params_expr=None, as_name=None):
        self.name = name
        self.params_expr = params_expr
        self.as_name = as_name

    def __repr__(self):
        return f"UrlNode(name='{self.name}', params_expr='{self.params_expr}', as_name='{self.as_name}')"


class StaticNode(Node):
    """Represents an @static('path') directive."""

    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return f"StaticNode(path='{self.path}')"


class CsrfNode(Node):
    """Represents an @csrf directive."""

    def __repr__(self):
        return "CsrfNode()"


class MethodNode(Node):
    """Represents an @method('POST') directive."""

    def __init__(self, method):
        self.method = method

    def __repr__(self):
        return f"MethodNode(method='{self.method}')"


class StyleNode(Node):
    """Represents an @style(dict) directive."""

    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return f"StyleNode(expression='{self.expression}')"


class ClassNode(Node):
    """Represents an @class(dict) directive."""

    def __init__(self, expression):
        self.expression = expression

    def __repr__(self):
        return f"ClassNode(expression='{self.expression}')"


class BreakNode(Node):
    """Represents an @break(condition) directive."""

    def __init__(self, condition=None):
        self.condition = condition

    def __repr__(self):
        return f"BreakNode(condition='{self.condition}')"


class ContinueNode(Node):
    """Represents an @continue(condition) directive."""

    def __init__(self, condition=None):
        self.condition = condition

class TransNode(Node):
    """Represents a @trans('message') directive."""

    def __init__(self, message, context=None, noop=False):
        self.message = message
        self.context = context
        self.noop = noop

    def __repr__(self):
        return f"TransNode(message='{self.message}', context='{self.context}', noop={self.noop})"


class BlockTranslateNode(Node):
    """Represents an @blocktranslate...@plural...@endblocktranslate block."""

    def __init__(self, body, plural_body=None, count=None, context=None, trimmed=False):
        self.body = body
        self.plural_body = plural_body
        self.count = count
        self.context = context
        self.trimmed = trimmed

    def __repr__(self):
        return f"BlockTranslateNode(body={self.body}, plural_body={self.plural_body}, count='{self.count}', context='{self.context}', trimmed={self.trimmed}')"


class WithNode(Node):
    """Represents a @with(vars)...@endwith block."""

    def __init__(self, variables, body):
        self.variables = variables  # Dictionary or list of assignments
        self.body = body

    def __repr__(self):
        return f"WithNode(variables={self.variables}, body={self.body})"


class NowNode(Node):
    """Represents a @now('format') directive."""

    def __init__(self, format_string):
        self.format_string = format_string

    def __repr__(self):
        return f"NowNode(format_string='{self.format_string}')"


class RegroupNode(Node):
    """Represents a @regroup(target, by, as_name) directive."""

    def __init__(self, target, by, as_name):
        self.target = target
        self.by = by
        self.as_name = as_name

    def __repr__(self):
        return f"RegroupNode(target='{self.target}', by='{self.by}', as_name='{self.as_name}')"


class SelectedNode(Node):
    """Represents a @selected(condition) directive."""

    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"SelectedNode(condition='{self.condition}')"


class RequiredNode(Node):
    """Represents a @required(condition) directive."""

    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"RequiredNode(condition='{self.condition}')"


class CheckedNode(Node):
    """Represents a @checked(condition) directive."""

    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"CheckedNode(condition='{self.condition}')"


class AutocompleteNode(Node):
    """Represents a @autocomplete(value) directive."""

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"AutocompleteNode(value='{self.value}')"


class RatioNode(Node):
    """Represents a @ratio(w, h) directive."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __repr__(self):
        return f"RatioNode(width='{self.width}', height='{self.height}')"


class GetStaticPrefixNode(Node):
    """Represents a @get_static_prefix directive."""
    def __repr__(self):
        return "GetStaticPrefixNode()"


class GetMediaPrefixNode(Node):
    """Represents a @get_media_prefix directive."""
    def __repr__(self):
        return "GetMediaPrefixNode()"


class QuerystringNode(Node):
    """Represents a @querystring(kwargs) directive."""

    def __init__(self, kwargs_expr):
        self.kwargs_expr = kwargs_expr

    def __repr__(self):
        return f"QuerystringNode(kwargs_expr='{self.kwargs_expr}')"


class LiveBladeNode(Node):
    """Represents a @liveblade directive."""
    def __repr__(self):
        return "LiveBladeNode()"


class BlockNode(Node):
    """Represents a @block('name')...@endblock block (Django style)."""

    def __init__(self, name, body):
        self.name = name
        self.body = body

    def __repr__(self):
        return f"BlockNode(name='{self.name}', body={self.body})"
