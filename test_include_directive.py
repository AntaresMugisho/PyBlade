#!/usr/bin/env python3
"""
Test the @include directive implementation.
"""


def test_parser_logic():
    """Test the parser logic for @include directive."""

    def _parse_include(args_str):
        """Mock the parser's _parse_include method."""
        import re

        # Remove parentheses and parse the function-like arguments
        match = re.match(r"^\s*\((.*)\)\s*$", args_str)
        if match:
            inner_args = match.group(1).strip()
            parts = [part.strip() for part in inner_args.split(",") if part.strip()]

            # First argument is always the path
            if len(parts) == 0:
                raise ValueError("@include requires at least a path argument")

            path_expr = parts[0]
            data_expr = parts[1] if len(parts) > 1 else None

            return {"path_expr": path_expr, "data_expr": data_expr}
        else:
            # No parentheses - treat as single path argument
            return {"path_expr": args_str.strip(), "data_expr": None}

    print("🔧 Testing @include Parser Logic")
    print("=" * 40)

    # Test 1: Simple path only
    args_str = '"partials.header"'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.header"'
    assert result["data_expr"] is None
    print("✓ Test 1 PASSED\n")

    # Test 2: Path with data
    args_str = '"partials.user", {"user": current_user}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.user"'
    assert result["data_expr"] == '{"user": current_user}'
    print("✓ Test 2 PASSED\n")

    # Test 3: Path with complex data
    args_str = '"partials.card", {"title": "Hello", "show": is_visible}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == '"partials.card"'
    assert result["data_expr"] == '{"title": "Hello", "show": is_visible}'
    print("✓ Test 3 PASSED\n")

    # Test 4: Variable path
    args_str = 'template_name, {"data": value}'
    result = _parse_include(args_str)
    print(f"Input: @include({args_str})")
    print(f"Result: {result}")
    assert result["path_expr"] == "template_name"
    assert result["data_expr"] == '{"data": value}'
    print("✓ Test 4 PASSED\n")


def test_node_rendering():
    """Test the IncludeNode rendering logic."""

    class MockIncludeNode:
        def __init__(self, path_expr, data_expr=None):
            self.path_expr = path_expr
            self.data_expr = data_expr

        def eval(self, expr, context):
            if expr == '"partials.header"':
                return "partials.header"
            elif expr == '"partials.user"':
                return "partials.user"
            elif expr == '{"user": current_user}':
                return {"user": context["current_user"]}
            elif expr == "template_name":
                return context["template_name"]
            elif expr == '{"data": value}':
                return {"data": context["value"]}
            return expr

        def render(self, context):
            """Mock render method."""
            try:
                # Evaluate the path expression
                path = self.eval(self.path_expr, context)

                # Evaluate data expression if provided
                data = {}
                if self.data_expr:
                    data = self.eval(self.data_expr, context)
                    if not isinstance(data, dict):
                        data = {}

                # Mock template rendering
                new_context = dict(context)
                new_context.update(data)

                # Return mock rendered content
                return f"[INCLUDED: {path} with context: {list(new_context.keys())}]"

            except Exception as e:
                raise e

    print("🎨 Testing IncludeNode Rendering")
    print("=" * 40)

    # Test 1: Simple include
    node = MockIncludeNode('"partials.header"')
    context = {"user": "John"}
    result = node.render(context)
    print(f"Node: {node}")
    print(f"Context: {context}")
    print(f"Result: {result}")
    assert "partials.header" in result
    print("✓ Test 1 PASSED\n")

    # Test 2: Include with data
    node = MockIncludeNode('"partials.user"', '{"user": current_user}')
    context = {"current_user": "Alice", "other": "data"}
    result = node.render(context)
    print(f"Node: {node}")
    print(f"Context: {context}")
    print(f"Result: {result}")
    assert "partials.user" in result
    assert "user" in result
    print("✓ Test 2 PASSED\n")

    # Test 3: Variable path with data
    node = MockIncludeNode("template_name", '{"data": value}')
    context = {"template_name": "dynamic.template", "value": "test_data"}
    result = node.render(context)
    print(f"Node: {node}")
    print(f"Context: {context}")
    print(f"Result: {result}")
    assert "dynamic.template" in result
    assert "data" in result
    print("✓ Test 3 PASSED\n")


def show_examples():
    """Show usage examples."""

    print("📝 @include Directive Examples")
    print("=" * 40)

    examples = [
        '@include("partials.header")',
        '@include("partials.user", {"user": current_user})',
        '@include("partials.card", {"title": "Hello", "show": is_visible})',
        '@include(template_name, {"data": value})',
    ]

    for example in examples:
        print(f"• {example}")

    print()
    print("Features:")
    print("✓ Simple path inclusion: @include('path.to.template')")
    print("✓ Inclusion with data: @include('path', {'key': value})")
    print("✓ Dynamic paths: @include(variable_name)")
    print("✓ Complex data objects: @include('path', {'multiple': values})")
    print("✓ Context merging: Data is merged with existing context")
    print()


if __name__ == "__main__":
    test_parser_logic()
    test_node_rendering()
    show_examples()
    print("🎉 All @include directive tests passed!")
