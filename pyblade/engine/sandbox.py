import ast
import operator
import math
from typing import Any, Dict, Optional, Set, Union
from functools import reduce


class SafeEvalException(Exception):
    """Custom exception for safe_eval errors."""
    pass


def _get_allowed_builtins() -> Dict[str, Any]:
    """Get a dictionary of allowed built-in functions and constants."""
    return {
        # Basic operations
        'len': len,
        'range': range,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'reversed': reversed,
        
        # Type conversions
        'int': int,
        'float': float,
        'str': str,
        'bool': bool,
        'list': list,
        'tuple': tuple,
        'dict': dict,
        'set': set,
        
        # Math operations
        'abs': abs,
        'round': round,
        'sum': sum,
        'min': min,
        'max': max,
        'pow': pow,
        
        # Math constants
        'pi': math.pi,
        'e': math.e,
        
        # Boolean constants
        'True': True,
        'False': False,
        'None': None,
    }


def _get_allowed_operators() -> Dict[type, Any]:
    """Get a dictionary of allowed operators."""
    return {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
        ast.MatMult: operator.matmul,
        
        # Comparison operators
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda x, y: x in y,
        ast.NotIn: lambda x, y: x not in y,
        
        # Unary operators
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
        ast.Invert: operator.invert,
    }


def _get_safe_nodes() -> Set[type]:
    """Get a set of allowed AST node types."""
    return {
        # Basic nodes
        ast.Module,
        ast.Expression,
        ast.Interactive,
        
        # Literals
        ast.Constant,
        ast.Num,
        ast.Str,
        ast.Bytes,
        ast.List,
        ast.Tuple,
        ast.Set,
        ast.Dict,
        ast.NameConstant,
        ast.Name,
        
        # Operations
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.Call,
        
        # Comprehensions
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
        ast.GeneratorExp,
        ast.comprehension,
        
        # Context
        ast.Load,
        ast.Store,
        
        # Boolean operations
        ast.And,
        ast.Or,
        
        # Subscripting
        ast.Subscript,
        ast.Index,
        ast.Slice,
        
        # Attribute access
        ast.Attribute,
    }


def safe_eval(
    expression: str,
    allowed_globals: Optional[Dict[str, Any]] = None,
    allowed_locals: Optional[Dict[str, Any]] = None,
    mode: str = "eval",
    max_string_length: int = 120,
    max_power: int = 100,
    timeout: Optional[float] = 1.0,
) -> Any:
    """
    Safely evaluate Python expressions with enhanced security features.
    
    Args:
        expression: The Python code string to evaluate
        allowed_globals: Additional allowed global variables/functions
        allowed_locals: Additional allowed local variables
        mode: Evaluation mode ('eval' or 'exec')
        max_string_length: Maximum allowed length for string literals
        max_power: Maximum allowed power operation value
        timeout: Maximum execution time in seconds (None for no limit)
    
    Returns:
        The result of the evaluated expression
    
    Raises:
        SafeEvalException: If the expression is unsafe or evaluation fails
        TimeoutError: If execution exceeds the timeout
    """
    if not isinstance(expression, str):
        raise SafeEvalException("Expression must be a string")
    
    if len(expression) > max_string_length:
        raise SafeEvalException(f"Expression too long (max {max_string_length} characters)")
    
    if mode not in ("eval", "exec"):
        raise SafeEvalException("Mode must be 'eval' or 'exec'")
    
    # Set up the execution environment
    safe_globals = {"__builtins__": None}
    if allowed_globals:
        safe_globals.update(allowed_globals)
    
    safe_locals = _get_allowed_builtins()
    if allowed_locals:
        safe_locals.update(allowed_locals)
    
    try:
        # Parse the AST
        try:
            tree = ast.parse(expression, mode=mode)
        except SyntaxError as e:
            raise SafeEvalException(f"Syntax error: {str(e)}")
        
        # Validate the AST
        if not _is_safe_ast(tree, max_power):
            raise SafeEvalException("Unsafe expression detected")
        
        # Compile the AST
        try:
            compiled_code = compile(tree, "<string>", mode)
        except Exception as e:
            raise SafeEvalException(f"Compilation error: {str(e)}")
        
        # Execute with timeout if specified
        if timeout is not None:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Execution timed out")
            
            # Set up the timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(int(timeout))
        
        try:
            if mode == "exec":
                return exec(compiled_code, safe_globals, safe_locals)
            return eval(compiled_code, safe_globals, safe_locals)
        finally:
            if timeout is not None:
                signal.alarm(0)
    
    except TimeoutError:
        raise
    except Exception as e:
        raise SafeEvalException(f"Evaluation error: {str(e)}")


def safe_exec(
    expression: str,
    allowed_globals: Optional[Dict[str, Any]] = None,
    allowed_locals: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """
    Safely execute Python code with enhanced security features.
    
    This is a wrapper around safe_eval with mode='exec'.
    """
    return safe_eval(expression, allowed_globals, allowed_locals, mode="exec", **kwargs)


def _is_safe_ast(node: ast.AST, max_power: int = 100) -> bool:
    """
    Recursively validate that an AST contains only safe operations.
    
    Args:
        node: The AST node to check
        max_power: Maximum allowed power operation value
    
    Returns:
        bool: True if the AST is safe, False otherwise
    """

    print(node)

    if not isinstance(node, tuple(_get_safe_nodes())):
        return False
    
    # Check for unsafe power operations
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)):
            if abs(node.right.value) > max_power:
                return False
    
    # Check for unsafe attribute access
    if isinstance(node, ast.Attribute):
        # Only allow certain attributes on certain types
        allowed_attributes = {
            'str': {'lower', 'upper', 'strip', 'lstrip', 'rstrip', 'split', 'join'},
            'list': {'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count', 'sort', 'reverse'},
            'dict': {'keys', 'values', 'items', 'get', 'clear', 'copy', 'pop'},
            'set': {'add', 'remove', 'discard', 'pop', 'clear', 'union', 'intersection', 'difference'},
        }
        
        # Check if the attribute access is allowed
        if isinstance(node.value, ast.Name):
            obj_type = node.value.id
            if obj_type in allowed_attributes and node.attr in allowed_attributes[obj_type]:
                return True
        return False
    
    # Recursively check child nodes
    for child in ast.iter_child_nodes(node):
        if not _is_safe_ast(child, max_power):
            return False
    
    return True
