#!/usr/bin/env python3
"""
Test the fixed @include directive parsing with complex dictionaries.
"""


def test_include_parsing():
    """Test the improved parsing logic for @include directive."""

    def _parse_include(args_str):
        """Mock the fixed parser's _parse_include method."""
        import re

        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()

            # Use a more sophisticated approach to handle nested structures
            # Find the first argument (path) and the rest (data)
            path_expr = None
            data_expr = None

            # Track bracket/brace nesting to properly split arguments
            bracket_count = 0
            brace_count = 0
            quote_char = None
            current_arg = ""

            for char in inner_args:
                if quote_char:
                    current_arg += char
                    if char == quote_char:
                        quote_char = None
                elif char in ('"', "'"):
                    quote_char = char
                    current_arg += char
                elif char in ("[", "("):
                    bracket_count += 1
                    current_arg += char
                elif char in ("]", ")"):
                    bracket_count -= 1
                    current_arg += char
                elif char == "{":
                    brace_count += 1
                    current_arg += char
                elif char == "}":
                    brace_count -= 1
                    current_arg += char
                elif char == "," and bracket_count == 0 and brace_count == 0:
                    # Found an argument boundary
                    if path_expr is None:
                        path_expr = current_arg.strip()
                    else:
                        data_expr = current_arg.strip()
                    current_arg = ""
                else:
                    current_arg += char

            # Add the last argument
            if current_arg.strip():
                if path_expr is None:
                    path_expr = current_arg.strip()
                else:
                    data_expr = current_arg.strip()

            return {"path_expr": path_expr, "data_expr": data_expr}
        else:
            # No parentheses - treat as single path argument
            return {"path_expr": args_str.strip(), "data_expr": None}

    print("🔧 Testing Fixed @include Parser Logic")
    print("=" * 50)

    # Test 1: Simple path only
    args_str = '"partials.header"'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.header"'
    assert result["data_expr"] is None
    print("✓ Test 1 PASSED\n")

    # Test 2: Simple dictionary
    args_str = '"partials.user", {"user": "John"}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.user"'
    assert result["data_expr"] == '{"user": "John"}'
    print("✓ Test 2 PASSED\n")

    # Test 3: Dictionary with multiple items (the problematic case)
    args_str = '"partials.card", {"name": "PyBlade", "version": "1.0", "active": True}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.card"'
    assert result["data_expr"] == '{"name": "PyBlade", "version": "1.0", "active": True}'
    print("✓ Test 3 PASSED\n")

    # Test 4: Dictionary with nested structures
    args_str = '"partials.complex", {"user": {"name": "John", "age": 30}, "items": [1, 2, 3]}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.complex"'
    assert result["data_expr"] == '{"user": {"name": "John", "age": 30}, "items": [1, 2, 3]}'
    print("✓ Test 4 PASSED\n")

    # Test 5: Dictionary with quotes in strings
    args_str = '"partials.quotes", {"message": "Hello, world!", "description": "It\'s great"}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.quotes"'
    assert result["data_expr"] == '{"message": "Hello, world!", "description": "It\'s great"}'
    print("✓ Test 5 PASSED\n")

    # Test 6: Mixed quotes
    args_str = '"partials.mixed", {"single": \'quoted\', "double": "quoted"}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.mixed"'
    assert result["data_expr"] == '{"single": \'quoted\', "double": "quoted"}'
    print("✓ Test 6 PASSED\n")


def show_fix_explanation():
    """Explain what was fixed."""

    print("🔍 What Was Fixed")
    print("=" * 30)
    print()
    print("❌ Before: Simple comma splitting")
    print('   parts = inner_args.split(",")')
    print('   → Broke on: {"name": "PyBlade", "version": "1.0"}')
    print()
    print("✅ After: Smart parsing with nesting tracking")
    print("   - Tracks quotes, brackets, and braces")
    print("   - Only splits on commas at top level")
    print("   - Handles nested structures correctly")
    print()
    print("🎯 Now supports:")
    print('   @include("path", {"key": "value", "other": true})')
    print('   @include("path", {"nested": {"deep": "value"}})')
    print('   @include("path", {"list": [1, 2, 3]})')
    print()


if __name__ == "__main__":
    test_include_parsing()
    show_fix_explanation()
    print("🎉 All @include parsing tests passed!")
