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
