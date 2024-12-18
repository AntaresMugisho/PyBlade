"""Tests for template directives."""
import pytest
from pyblade.engine.parsing.directives import DirectiveParser


def test_parse_if_directive():
    """Test parsing @if directives."""
    parser = DirectiveParser()
    template = "@if(condition)content@endif"
    
    result = parser.parse_directives(template, {"condition": True})
    assert result == "content"
    
    result = parser.parse_directives(template, {"condition": False})
    assert result == ""


def test_parse_else_directive():
    """Test parsing @else directives."""
    parser = DirectiveParser()
    template = "@if(condition)true@else false@endif"
    
    result = parser.parse_directives(template, {"condition": True})
    assert result == "true"
    
    result = parser.parse_directives(template, {"condition": False})
    assert result == "false"


def test_parse_elif_directive():
    """Test parsing @elif directives."""
    parser = DirectiveParser()
    template = "@if(a)A@elif(b)B@else C@endif"
    
    result = parser.parse_directives(template, {"a": True, "b": False})
    assert result == "A"
    
    result = parser.parse_directives(template, {"a": False, "b": True})
    assert result == "B"
    
    result = parser.parse_directives(template, {"a": False, "b": False})
    assert result == "C"


def test_nested_if_directives():
    """Test parsing nested @if directives."""
    parser = DirectiveParser()
    template = """
    @if(outer)
        Outer
        @if(inner)
            Inner
        @endif
    @endif
    """
    
    # Test both conditions true
    result = parser.parse_directives(template, {"outer": True, "inner": True})
    assert "Outer" in result
    assert "Inner" in result
    
    # Test outer true, inner false
    result = parser.parse_directives(template, {"outer": True, "inner": False})
    assert "Outer" in result
    assert "Inner" not in result
    
    # Test outer false - inner should not be evaluated
    result = parser.parse_directives(template, {"outer": False, "inner": True})
    assert "Outer" not in result
    assert "Inner" not in result


def test_complex_if_elif_else():
    """Test complex if-elif-else scenarios."""
    parser = DirectiveParser()
    template = """
    @if(name == "Antares")
        <p>You are registered.</p>
    @elif(name == "B")
        <p>You are B</p>
    @elif(name == "C")
        <p>You are C</p>
    @elif(name == "Anta")
        @if(1 > 0)
            <p>1 is greater than 0</p>
        @else
            <p>1 is not less than 0</p>
        @endif
        <p>You are registered as {{name}}.</p>
    @endif
    """
    
    # Test first condition (Antares)
    result = parser.parse_directives(template, {"name": "Antares"})
    assert "<p>You are registered.</p>" in result
    assert "1 is greater than 0" not in result  # Nested if should not be evaluated
    assert "@endif" not in result  # @endif should not appear in output
    
    # Test second condition (B)
    result = parser.parse_directives(template, {"name": "B"})
    assert "<p>You are B</p>" in result
    assert "You are registered." not in result
    
    # Test nested if condition (Anta)
    result = parser.parse_directives(template, {"name": "Anta"})
    assert "1 is greater than 0" in result
    assert "You are registered as Anta" in result
    assert "1 is not less than 0" not in result


def test_if_with_expressions():
    """Test if directives with complex expressions."""
    parser = DirectiveParser()
    template = """
    @if(len(items) > 2 and name.startswith('A'))
        Complex condition met
    @endif
    """
    
    # Test complex condition true
    result = parser.parse_directives(template, {
        "items": [1, 2, 3],
        "name": "Antares"
    })
    assert "Complex condition met" in result
    
    # Test complex condition false
    result = parser.parse_directives(template, {
        "items": [1],
        "name": "Antares"
    })
    assert "Complex condition met" not in result


def test_if_error_handling():
    """Test error handling in if directives."""
    parser = DirectiveParser()
    template = "@if(undefined_var)content@endif"
    
    with pytest.raises(Exception) as exc_info:
        parser.parse_directives(template, {})
    assert "undefined_var" in str(exc_info.value)


def test_multiple_nested_if():
    """Test multiple levels of nested if statements."""
    parser = DirectiveParser()
    template = """
    @if(a)
        Level 1
        @if(b)
            Level 2
            @if(c)
                Level 3
            @endif
        @endif
    @endif
    """
    
    # Test all conditions true
    result = parser.parse_directives(template, {"a": True, "b": True, "c": True})
    assert "Level 1" in result
    assert "Level 2" in result
    assert "Level 3" in result
    
    # Test first two levels true
    result = parser.parse_directives(template, {"a": True, "b": True, "c": False})
    assert "Level 1" in result
    assert "Level 2" in result
    assert "Level 3" not in result
    
    # Test only first level true
    result = parser.parse_directives(template, {"a": True, "b": False, "c": True})
    assert "Level 1" in result
    assert "Level 2" not in result
    assert "Level 3" not in result


def test_nested_if_in_elif():
    """Test nested if statements within elif blocks."""
    parser = DirectiveParser()
    template = """
    @if(a)
        A
    @elif(b)
        @if(c)
            B and C
        @else
            Only B
        @endif
    @endif
    """
    
    # Test nested if in elif (true case)
    result = parser.parse_directives(template, {"a": False, "b": True, "c": True})
    assert "B and C" in result
    assert "Only B" not in result
    
    # Test nested if in elif (false case)
    result = parser.parse_directives(template, {"a": False, "b": True, "c": False})
    assert "B and C" not in result
    assert "Only B" in result
    
    # Test first condition true (should skip elif)
    result = parser.parse_directives(template, {"a": True, "b": True, "c": True})
    assert "A" in result
    assert "B and C" not in result
    assert "Only B" not in result


def test_complex_conditions():
    """Test if statements with complex conditions."""
    parser = DirectiveParser()
    template = """
    @if(len(items) > 2 and (name.startswith('A') or role == 'admin'))
        Complex condition met
        @if(items[0] == 1)
            First item is 1
        @endif
    @endif
    """
    
    # Test complex condition with nested if (all true)
    result = parser.parse_directives(template, {
        "items": [1, 2, 3],
        "name": "Antares",
        "role": "user"
    })
    assert "Complex condition met" in result
    assert "First item is 1" in result
    
    # Test complex condition true but nested false
    result = parser.parse_directives(template, {
        "items": [2, 2, 3],
        "name": "Antares",
        "role": "user"
    })
    assert "Complex condition met" in result
    assert "First item is 1" not in result


def test_malformed_if_structure():
    """Test error handling for malformed if structures."""
    parser = DirectiveParser()
    
    # Missing @endif
    template = "@if(condition) content"
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"condition": True})
    assert "Malformed" in str(exc_info.value)
    
    # Mismatched @endif
    template = "@if(a) @if(b) nested @endif content"
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"a": True, "b": True})
    assert "Malformed" in str(exc_info.value)


def test_parse_for_directive():
    """Test parsing @for directives."""
    parser = DirectiveParser()
    template = "@for(item in items){{ item }}@endfor"
    context = {"items": [1, 2, 3]}
    
    result = parser.parse_directives(template, context)
    assert result == "123"


def test_nested_for_directive():
    """Test parsing nested @for directives."""
    parser = DirectiveParser()
    template = "@for(x in xs)@for(y in ys){{ x }}{{ y }}@endfor@endfor"
    context = {"xs": ["a", "b"], "ys": [1, 2]}
    
    result = parser.parse_directives(template, context)
    assert result == "a1a2b1b2"


def test_parse_auth_directive(mock_request):
    """Test parsing @auth directives."""
    parser = DirectiveParser()
    template = "@auth content @endauth"
    
    # Test with authenticated user
    mock_request.user.is_authenticated = True
    result = parser.parse_directives(template, {"request": mock_request})
    assert result == " content "
    
    # Test with unauthenticated user
    mock_request.user.is_authenticated = False
    result = parser.parse_directives(template, {"request": mock_request})
    assert result == ""


def test_parse_guest_directive(mock_request):
    """Test parsing @guest directives."""
    parser = DirectiveParser()
    template = "@guest content @endguest"
    
    # Test with authenticated user
    mock_request.user.is_authenticated = True
    result = parser.parse_directives(template, {"request": mock_request})
    assert result == ""
    
    # Test with unauthenticated user
    mock_request.user.is_authenticated = False
    result = parser.parse_directives(template, {"request": mock_request})
    assert result == " content "


def test_parse_props_directive():
    """Test parsing @props directives."""
    parser = DirectiveParser()
    template = """@props({
        'title': 'Default',
        'show': True
    })
    {{ title }}"""
    
    # Test with no props provided
    result = parser.parse_directives(template, {})
    assert "Default" in result
    
    # Test with props override
    result = parser.parse_directives(template, {"title": "Custom"})
    assert "Custom" in result


def test_parse_include_directive(template_dir):
    """Test parsing @include directives."""
    # Create an includable template
    include_path = template_dir / "partial.html"
    include_path.write_text("Included content")
    
    parser = DirectiveParser()
    template = "@include('partial.html')"
    
    result = parser.parse_directives(template, {"template_dir": template_dir})
    assert result == "Included content"


def test_parse_extends_directive(template_dir):
    """Test parsing @extends directives."""
    # Create a layout template
    layout_path = template_dir / "layout.html"
    layout_path.write_text("""
    <html>
        <body>
            @yield('content')
        </body>
    </html>
    """)
    
    parser = DirectiveParser()
    template = """
    @extends('layout.html')
    @section('content')
    Page content
    @endsection
    """
    
    result = parser.parse_directives(template, {"template_dir": template_dir})
    assert "Page content" in result
    assert "<html>" in result
    assert "</html>" in result


def test_switch_directive():
    """Test switch directive functionality."""
    parser = DirectiveParser()
    template = """
    @switch(value)
        @case(1)
            One
        @case(2)
            Two
        @case(3)
            Three
        @default
            Other
    @endswitch
    """
    
    # Test different cases
    result = parser.parse_directives(template, {"value": 1})
    assert "One" in result
    assert "Two" not in result
    
    result = parser.parse_directives(template, {"value": 2})
    assert "Two" in result
    assert "One" not in result
    
    result = parser.parse_directives(template, {"value": 3})
    assert "Three" in result
    
    # Test default case
    result = parser.parse_directives(template, {"value": 4})
    assert "Other" in result


def test_switch_with_expressions():
    """Test switch with complex expressions."""
    parser = DirectiveParser()
    template = """
    @switch(len(items))
        @case(0)
            Empty list
        @case(1)
            One item
        @case(2 + 1)
            Three items
        @default
            Multiple items
    @endswitch
    """
    
    result = parser.parse_directives(template, {"items": []})
    assert "Empty list" in result
    
    result = parser.parse_directives(template, {"items": [1]})
    assert "One item" in result
    
    result = parser.parse_directives(template, {"items": [1, 2, 3]})
    assert "Three items" in result
    
    result = parser.parse_directives(template, {"items": [1, 2, 3, 4]})
    assert "Multiple items" in result


def test_nested_switch_in_if():
    """Test switch directive nested inside if directive."""
    parser = DirectiveParser()
    template = """
    @if(show_switch)
        @switch(value)
            @case(1)
                One
            @case(2)
                Two
            @default
                Other
        @endswitch
    @endif
    """
    
    # Test switch when if is true
    result = parser.parse_directives(template, {"show_switch": True, "value": 1})
    assert "One" in result
    
    # Test switch when if is false
    result = parser.parse_directives(template, {"show_switch": False, "value": 1})
    assert "One" not in result


def test_unclosed_tags():
    """Test detection of unclosed directive tags."""
    parser = DirectiveParser()
    
    # Test unclosed if
    template = """
    @if(condition)
        Content
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"condition": True})
    assert "Unclosed @if directive at line 2" in str(exc_info.value)
    
    # Test unclosed switch
    template = """
    Line 1
    Line 2
    @switch(value)
        @case(1)
            One
        @case(2)
            Two
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"value": 1})
    assert "Unclosed @switch directive at line 4" in str(exc_info.value)
    
    # Test unclosed for
    template = """
    @for(item in items)
        {{ item }}
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"items": [1, 2, 3]})
    assert "Unclosed @for directive at line 2" in str(exc_info.value)


def test_switch_error_handling():
    """Test error handling in switch directives."""
    parser = DirectiveParser()
    
    # Test invalid switch expression
    template = """
    @switch(undefined_var)
        @case(1)
            One
    @endswitch
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {})
    assert "undefined_var" in str(exc_info.value)
    
    # Test invalid case expression
    template = """
    @switch(value)
        @case(undefined_var)
            One
    @endswitch
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"value": 1})
    assert "undefined_var" in str(exc_info.value)
