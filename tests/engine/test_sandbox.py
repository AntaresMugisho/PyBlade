"""Tests for the sandbox module."""
import pytest
import math
from pyblade.engine.sandbox import safe_eval, safe_exec, SafeEvalException


def test_basic_operations():
    """Test basic arithmetic operations."""
    assert safe_eval("2 + 2") == 4
    assert safe_eval("3 * 4") == 12
    assert safe_eval("10 / 2") == 5.0
    assert safe_eval("2 ** 3") == 8
    assert safe_eval("-5") == -5
    assert safe_eval("+5") == 5


def test_builtin_functions():
    """Test allowed built-in functions."""
    assert safe_eval("len([1, 2, 3])") == 3
    assert safe_eval("min(1, 2, 3)") == 1
    assert safe_eval("max(1, 2, 3)") == 3
    assert safe_eval("abs(-5)") == 5
    assert safe_eval("round(3.14159, 2)") == 3.14


def test_math_constants():
    """Test math constants."""
    assert safe_eval("pi") == math.pi
    assert safe_eval("e") == math.e


def test_type_conversions():
    """Test type conversion functions."""
    assert safe_eval("int('123')") == 123
    assert safe_eval("float('3.14')") == 3.14
    assert safe_eval("str(123)") == "123"
    assert safe_eval("bool(1)") is True
    assert safe_eval("list((1, 2, 3))") == [1, 2, 3]


def test_comprehensions():
    """Test list and dict comprehensions."""
    assert safe_eval("[x * 2 for x in range(3)]") == [0, 2, 4]
    assert safe_eval("{x: x**2 for x in range(3)}") == {0: 0, 1: 1, 2: 4}
    assert safe_eval("{x for x in range(3)}") == {0, 1, 2}


def test_string_operations():
    """Test string operations."""
    context = {"s": "Hello, World!"}
    assert safe_eval("s.lower()", allowed_locals=context) == "hello, world!"
    assert safe_eval("s.upper()", allowed_locals=context) == "HELLO, WORLD!"
    assert safe_eval("s.split(',')", allowed_locals=context) == ["Hello", " World!"]


def test_list_operations():
    """Test list operations."""
    context = {"lst": [1, 2, 3]}
    assert safe_eval("lst.index(2)", allowed_locals=context) == 1
    assert safe_eval("lst.count(1)", allowed_locals=context) == 1
    assert safe_eval("sorted([3, 1, 2])") == [1, 2, 3]
    assert safe_eval("reversed([1, 2, 3])", allowed_locals={"reversed": reversed}) == [3, 2, 1]


def test_dict_operations():
    """Test dictionary operations."""
    context = {"d": {"a": 1, "b": 2}}
    assert safe_eval("d.get('a')", allowed_locals=context) == 1
    assert safe_eval("list(d.keys())", allowed_locals=context) == ["a", "b"]
    assert safe_eval("list(d.values())", allowed_locals=context) == [1, 2]


def test_set_operations():
    """Test set operations."""
    context = {"s1": {1, 2, 3}, "s2": {3, 4, 5}}
    assert safe_eval("s1.union(s2)", allowed_locals=context) == {1, 2, 3, 4, 5}
    assert safe_eval("s1.intersection(s2)", allowed_locals=context) == {3}
    assert safe_eval("s1.difference(s2)", allowed_locals=context) == {1, 2}


def test_comparison_operations():
    """Test comparison operations."""
    assert safe_eval("1 < 2") is True
    assert safe_eval("2 <= 2") is True
    assert safe_eval("3 > 2") is True
    assert safe_eval("3 >= 3") is True
    assert safe_eval("2 == 2") is True
    assert safe_eval("1 != 2") is True
    assert safe_eval("1 in [1, 2, 3]") is True
    assert safe_eval("4 not in [1, 2, 3]") is True


def test_boolean_operations():
    """Test boolean operations."""
    assert safe_eval("True and True") is True
    assert safe_eval("True or False") is True
    assert safe_eval("not False") is True
    assert safe_eval("True and not False") is True


def test_error_handling():
    """Test error handling."""
    with pytest.raises(SafeEvalException):
        safe_eval("__import__('os')")
    
    with pytest.raises(SafeEvalException):
        safe_eval("open('file.txt')")
    
    with pytest.raises(SafeEvalException):
        safe_eval("globals()")
    
    with pytest.raises(SafeEvalException):
        safe_eval("locals()")
    
    with pytest.raises(SafeEvalException):
        safe_eval("eval('2 + 2')")
    
    with pytest.raises(SafeEvalException):
        safe_eval("exec('x = 1')")


def test_timeout():
    """Test timeout functionality."""
    with pytest.raises(TimeoutError):
        safe_eval("while True: pass", timeout=1)


def test_max_power():
    """Test maximum power restriction."""
    assert safe_eval("2 ** 10") == 1024  # Should work
    with pytest.raises(SafeEvalException):
        safe_eval("2 ** 1000")  # Should fail


def test_max_string_length():
    """Test maximum string length restriction."""
    with pytest.raises(SafeEvalException):
        safe_eval("x" * 20000)


def test_safe_exec():
    """Test safe_exec functionality."""
    context = {}
    safe_exec("x = 1 + 1", allowed_locals=context)
    assert context.get("x") == 2


def test_custom_globals():
    """Test custom global variables."""
    def custom_function(x):
        return x * 2
    
    globals = {"double": custom_function}
    assert safe_eval("double(5)", allowed_globals=globals) == 10


def test_custom_locals():
    """Test custom local variables."""
    locals = {"x": 10, "y": 20}
    assert safe_eval("x + y", allowed_locals=locals) == 30
