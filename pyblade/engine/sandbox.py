import ast


def safe_eval(expression, allowed_globals=None, allowed_locals=None, mode: str = "eval"):
    """
    Function to evaluate safe expressions like numbers, lists, tuples, dicts...

    :param expression: The python code string to evaluate
    :param allowed_globals: Whitelist specific safe built-ins functions
    :param allowed_locals: Whitelist specific safe variables
    :return: The safe evaluated expression result
    """

    if allowed_globals is None:
        allowed_globals = {
            "__builtins__": None,
        }

    if allowed_locals is None:
        allowed_locals = {}

    allowed_builtins = {
        "len": len,
        "range": range,
        "min": min,
        "max": max,
        "True": True,
        "False": False,
        "None": None,
    }

    try:
        node = ast.parse(expression, mode=mode)
        if not _is_safe_node(node):
            raise ValueError("Unsafe expression detected !")

        compiled_node = compile(node, filename="", mode=mode)

        if mode == "exec":
            return exec(compiled_node, allowed_globals, {**allowed_builtins, **allowed_locals})
        return eval(compiled_node, allowed_globals, {**allowed_builtins, **allowed_locals})

    except Exception as e:
        raise ValueError(f"Error evaluating expression: {e}")


def safe_exec(expression, allowed_globals=None, allowed_locals=None):
    safe_eval(expression, allowed_globals, allowed_locals, mode="exec")


def _is_safe_node(node):
    """
    Recursively ensure that the AST node contains only safe expressions

    :param node:
    :return: Tha AST node obtained after parsing
    """
    safe_nodes = (
        ast.Expression,
        ast.Num,
        ast.Str,
        ast.BinOp,
        ast.UnaryOp,
        ast.Compare,
        ast.Name,
        ast.Load,
        ast.Call,
        ast.List,
        ast.Dict,
        ast.Tuple,
        ast.BoolOp,
        ast.ListComp,
        ast.DictComp,
        ast.SetComp,
        ast.GeneratorExp,
        ast.Constant,
    )

    if not isinstance(node, safe_nodes):
        return False

    for child in ast.iter_child_nodes(node):
        if not _is_safe_node(child):
            return False
    return True
