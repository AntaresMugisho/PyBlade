import ast
import operator
import re

from .filters import filters


class SafeEvaluator:
    """AST-based safe expression evaluator for templates with filter fallback."""

    _operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

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

    _safe_methods = {
        str: {
            "upper",
            "lower",
            "strip",
            "lstrip",
            "rstrip",
            "title",
            "capitalize",
            "casefold",
            "swapcase",
            "startswith",
            "endswith",
            "replace",
        },
        list: {"count", "index"},
        tuple: {"count", "index"},
        dict: {"get", "keys", "values", "items"},
    }

    _filters = filters

    def evaluate(self, expression, context):
        if not expression:
            return None

        if not isinstance(expression, str):
            return expression

        # Handle Numeric attributes (for lists or tuples, e.g.: items.0)
        expr = expression.strip()
        m = re.fullmatch(r"([a-zA-Z_][a-zA-Z0-9_]*)\.(-?\d+)", expr)
        if m:
            expr = f"{m.group(1)}[{m.group(2)}]"

        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError as exc:
            raise TypeError(f"Invalid expression syntax: {expression!r}") from exc

        return self._eval_node(tree.body, context or {})

    def _is_safe_method(self, owner, method_name):
        for typ, allowed in self._safe_methods.items():
            if isinstance(owner, typ):
                return method_name in allowed
        return False

    def _eval_node(self, node, context):

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            if node.id in self._builtins:
                return self._builtins[node.id]
            return context.get(node.id)

        # ----------------------------
        # ATTRIBUTE RESOLUTION
        # ----------------------------
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("_"):
                raise AttributeError("Access to private attribute is not allowed in templates")

            owner = self._eval_node(node.value, context)
            if owner is None:
                return None

            attr_name = node.attr

            # Dict key lookup
            if isinstance(owner, dict) and attr_name in owner:
                return owner[attr_name]

            # List/Tuple numeric index (my_list.0)
            # if attr_name.lstrip("-").isdigit() and isinstance(owner, (list, tuple)):
            #     try:
            #         return owner[int(attr_name)]
            #     except Exception:
            #         return None

            # Normal attribute lookup
            try:
                value = getattr(owner, attr_name)
            except AttributeError:
                # Fallback to filter (no-arg filter)
                if self._filters and self._filters.has(attr_name):
                    filter_func = self._filters.get(attr_name)
                    return filter_func(owner)
                return None

            # Auto-call zero-arg bound methods
            if callable(value) and hasattr(value, "__self__"):
                if self._is_safe_method(owner, attr_name):
                    try:
                        return value()
                    except TypeError:
                        return value

            return value

        # ----------------------------
        # CALL SUPPORT (method OR filter with args)
        # ----------------------------
        if isinstance(node, ast.Call):

            # If this is something like value.truncate(20)
            if isinstance(node.func, ast.Attribute):
                attr_node = node.func
                owner = self._eval_node(attr_node.value, context)

                if owner is None:
                    return None

                attr_name = attr_node.attr

                args = [self._eval_node(arg, context) for arg in node.args]
                kwargs = {kw.arg: self._eval_node(kw.value, context) for kw in node.keywords}

                # Try normal attribute method first
                if hasattr(owner, attr_name):
                    method = getattr(owner, attr_name)
                    if callable(method):
                        if self._is_safe_method(owner, attr_name):
                            return method(*args, **kwargs)
                        raise PermissionError(f"Calling method '{attr_name}' is not allowed in templates")

                # Fallback to filter
                if self._filters and self._filters.has(attr_name):
                    filter_func = self._filters.get(attr_name)
                    return filter_func(owner, *args, **kwargs)

                return None

            # Normal function call
            func = self._eval_node(node.func, context)
            if func is None:
                raise TypeError("Attempted to call a non-existent function")

            args = [self._eval_node(arg, context) for arg in node.args]
            kwargs = {kw.arg: self._eval_node(kw.value, context) for kw in node.keywords}
            return func(*args, **kwargs)

        # ----------------------------
        # OPERATORS
        # ----------------------------
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported binary operator: {op_type.__name__}")
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            return self._operators[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
            operand = self._eval_node(node.operand, context)
            return self._operators[op_type](operand)

        if isinstance(node, ast.BoolOp):
            op_type = type(node.op)
            if op_type not in self._operators:
                raise TypeError(f"Unsupported boolean operator: {op_type.__name__}")
            values = [self._eval_node(v, context) for v in node.values]
            result = values[0]
            for v in values[1:]:
                result = self._operators[op_type](result, v)
            return result

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

        if isinstance(node, ast.Subscript):
            target = self._eval_node(node.value, context)
            if target is None:
                return None

            index_node = node.slice
            if isinstance(index_node, ast.Constant):
                key = index_node.value
            else:
                key = self._eval_node(index_node, context)

            try:
                return target[key]
            except Exception:
                raise TypeError(f"Invalid index/key access on object of type {type(target).__name__}")

        if isinstance(node, ast.List):
            return [self._eval_node(elt, context) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt, context) for elt in node.elts)

        if isinstance(node, ast.Dict):
            return {self._eval_node(k, context): self._eval_node(v, context) for k, v in zip(node.keys, node.values)}

        raise TypeError(f"Unsupported syntax in template expression: {type(node).__name__}")
