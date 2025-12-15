from typing import Any, Dict

from .wrappers import TDict, wrap_value


SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "bool": bool,
    "enumerate": enumerate,
    "zip": zip,
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
    "sum": sum,
    "type": type
}


def safe_eval(
    expression: str,
    context: Dict[str, Any] | None = None,
    builtins: Dict[str, Any] | None = None,
):
    if builtins is None:
        builtins = SAFE_BUILTINS
    try:
        return eval(expression, {"__builtins__": builtins}, context)
    except Exception as e:
        raise e


class ExpressionEvaluator:
    """
    Evaluates template expressions with support for method chaining
    and automatic type wrapping.
    """

    def __init__(self, context):
        self.context = context

    def evaluate(self, expression):
        """
        Evaluate an expression with method chaining support.
        Handles cases like: post.title.slugify.excerpt
        """
        # First, check if this is a simple Python expression (no dots for chaining)
        # If it contains operators or is a literal, use eval
        if not self._is_chainable_expression(expression):
            try:
                return safe_eval(expression, self.context)
            except Exception:
                # If eval fails, try to parse as attribute access
                pass

        # Parse the expression to handle method chaining
        parts = self._parse_expression(expression)

        if not parts:
            return None

        # Start with the base context
        result = self.context

        for part in parts:
            if part["type"] == "attribute":
                # Access attribute or dictionary key
                if isinstance(result, dict):
                    result = result.get(part["name"])
                    if result is None:
                        return None
                elif isinstance(result, TDict):
                    # Access the internal dictionary of TDict
                    result = result._value.get(part["name"])
                    if result is None:
                        return None
                else:
                    result = getattr(result, part["name"], None)
                    if result is None:
                        return None

                # Check if the result is a callable method (without parentheses)
                # If so, call it automatically for methods that take no required args
                if callable(result):
                    try:
                        # Try calling with no arguments
                        result = result()
                    except TypeError:
                        # Method requires arguments, leave it as is
                        pass

                # Wrap the result for method chaining
                result = wrap_value(result)

            elif part["type"] == "method":
                # Call method with or without arguments
                method_name = part["name"]
                args = part.get("args", [])
                kwargs = part.get("kwargs", {})

                if hasattr(result, method_name):
                    method = getattr(result, method_name)
                    if callable(method):
                        result = method(*args, **kwargs)
                        result = wrap_value(result)
                    else:
                        result = method
                        result = wrap_value(result)
                else:
                    raise AttributeError(f"'{type(result).__name__}' has no attribute '{method_name}'")

            elif part["type"] == "index":
                # Handle indexing like list[0] or dict['key']
                index = part["index"]
                if isinstance(result, (list, tuple)):
                    result = result[index]
                elif isinstance(result, dict):
                    result = result.get(index)
                result = wrap_value(result)

        return result

    def _is_chainable_expression(self, expression):
        """Check if expression contains attribute/method chaining."""
        # If it has operators like +, -, *, /, etc., it's not a simple chain
        if any(
            op in expression
            for op in ["+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=", " and ", " or ", " not ", "(", ")"]
        ):
            return False
        # If it has dots, it's likely a chain
        return "." in expression

    def _parse_expression(self, expression):
        """
        Parse an expression into parts for evaluation.
        Handles: variable.attribute.method().method2.attribute2
        """
        parts = []

        # Split by dots but preserve method calls
        segments = expression.split(".")

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Check if this segment has parentheses (method call with args)
            if "(" in segment and segment.endswith(")"):
                method_name = segment[: segment.index("(")]
                args_str = segment[segment.index("(") + 1 : -1].strip()
                parts.append(
                    {
                        "type": "method",
                        "name": method_name,
                        "args": self._parse_args(args_str) if args_str else [],
                        "kwargs": {},
                    }
                )
            elif "[" in segment:
                # Handle indexing
                attr_name = segment[: segment.index("[")]
                if attr_name:
                    parts.append({"type": "attribute", "name": attr_name})
                index_str = segment[segment.index("[") + 1 : segment.index("]")].strip()
                try:
                    index = int(index_str)
                except ValueError:
                    index = index_str.strip("\"'")
                parts.append({"type": "index", "index": index})
            else:
                # Simple attribute access (could be a method without parens)
                parts.append({"type": "attribute", "name": segment})

        return parts

    def _parse_args(self, args_str):
        """Parse method arguments (simplified version)."""
        if not args_str:
            return []

        # Simple comma-separated parsing
        # TODO: handle nested structures properly
        args = []
        for arg in args_str.split(","):
            arg = arg.strip()
            try:
                # Try to evaluate as literal
                args.append(eval(arg, {"__builtins__": {}}, {}))
            except Exception:
                args.append(arg)
        return args
