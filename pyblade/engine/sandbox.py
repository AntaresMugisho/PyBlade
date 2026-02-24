import ast
import operator


class SafeEvaluator:
    """AST-based safe expression evaluator for templates.

    - Only allows a restricted set of Python expression constructs.
    - Whitelists math, comparison and boolean operators.
    - Whitelists a small set of builtin functions.
    - Blocks attribute access that starts with an underscore.
    """

    # Whitelist of safe operators
    _operators = {
        # Arithmetic
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        # Boolean
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
        # Comparisons
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    # Whitelist of safe built-ins
    _builtins = {
        "len": len,
        "range": range,
        "type": type,
        "sum": sum,
        "min": min,
        "max": max,
        "enumerate": enumerate,
        "bool": bool,
        "abs": abs,
    }

    def evaluate(self, expression, context):
        """Evaluate an expression string safely within the given context."""
        if not expression:
            return None

        if not isinstance(expression, str):
            return expression

        try:
            tree = ast.parse(expression.strip(), mode="eval")
        except SyntaxError as exc:
            raise TypeError(f"Invalid expression syntax: {expression!r}") from exc

        return self._eval_node(tree.body, context or {})

    def _eval_node(self, node, context):
        # Constants: 5, "hello"
        if isinstance(node, ast.Constant):
            return node.value

        # Names: variables or whitelisted builtins
        if isinstance(node, ast.Name):
            if node.id in self._builtins:
                return self._builtins[node.id]
            return context.get(node.id)

        # Attribute lookups: obj.attr
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise AttributeError("Access to private attribute is not allowed in templates")

            owner = self._eval_node(node.value, context)
            if owner is None:
                return None

            # Delegate to wrapper objects when present (e.g. TemplateVariable/T* wrappers)
            try:
                value = getattr(owner, node.attr)
            except AttributeError as exc:
                # For mapping-like wrappers that expose their own access API, just re-raise
                raise exc

            return value

        # Binary operations: a + b, a * b, etc.
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported binary operator: {op_type.__name__}")
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            return self._operators[op_type](left, right)

        # Unary operations: -a, not a
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand, context)
            return self._operators[op_type](operand)

        # Boolean operations: a and b, a or b
        if isinstance(node, ast.BoolOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported boolean operator: {op_type.__name__}")

            values = [self._eval_node(v, context) for v in node.values]
            result = values[0]
            for v in values[1:]:
                result = self._operators[op_type](result, v)
            return result

        # Comparisons: a < b, a == b, a < b < c
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, right_expr in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self._operators:
                    raise TypeError(f"Unsupported comparison operator: {op_type.__name__}")
                right = self._eval_node(right_expr, context)
                if not self._operators[op_type](left, right):
                    return False
                left = right
            return True

        # Function / method calls: func(arg1, arg2, ...)
        if isinstance(node, ast.Call):
            func = self._eval_node(node.func, context)
            if func is None:
                raise TypeError("Attempted to call a non-existent function")

            args = [self._eval_node(arg, context) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value, context) for kw in node.keywords}
            return func(*args, **kwargs)

        # Allow simple literal containers if needed (lists, tuples, dicts)
        if isinstance(node, ast.List):
            return [self._eval_node(elt, context) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt, context) for elt in node.elts)

        if isinstance(node, ast.Dict):
            return {self._eval_node(k, context): self._eval_node(v, context) for k, v in zip(node.keys, node.values)}

        raise TypeError(f"Unsupported syntax in template expression: {type(node).__name__}")
