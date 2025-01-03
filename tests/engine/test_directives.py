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
    
    # Test missing @endif
    template = """
    @if(condition)
        Content
    """
    with pytest.raises(DirectiveParsingError) as exc_info:
        parser.parse_directives(template, {"condition": True})
    assert "Malformed" in str(exc_info.value)
    
    # Test mismatched @endif
    template = """
    @if(a) @if(b) nested @endif content
    """
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
    assert result == "content"
    
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
    assert result == "content"


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
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives(template, {})
    assert "undefined_var" in str(exc.value)
    
    # Test invalid case expression
    template = """
    @switch(value)
        @case(undefined_var)
            One
    @endswitch
    """
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives(template, {"value": 1})
    assert "undefined_var" in str(exc.value)


def test_comment_directives():
    """Test both inline and block comments."""
    parser = DirectiveParser()
    
    # Test inline comments
    template = "Hello{# This is a comment #}World"
    result = parser.parse_directives(template, {})
    assert result == "HelloWorld"
    
    # Test block comments
    template = """
    Start
    @comment
        This is a
        multiline comment
    @endcomment
    End"""
    result = parser.parse_directives(template, {})
    assert "Start" in result and "End" in result
    assert "This is a" not in result
    
    # Test nested comments
    template = """
    @comment
        Outer comment
        {# Inner comment #}
    @endcomment
    """
    result = parser.parse_directives(template, {})
    assert result.strip() == ""


def test_verbatim_directives():
    """Test both verbatim blocks and shorthand verbatim."""
    parser = DirectiveParser()
    
    # Test verbatim block
    template = """
    @verbatim
        {{ user.name }}
        @if(condition)
            Content
        @endif
    @endverbatim
    """
    result = parser.parse_directives(template, {"user": {"name": "John"}})
    assert "{{ user.name }}" in result
    assert "@if(condition)" in result
    
    # Test shorthand verbatim
    template = "Normal: {{ value }}, Verbatim: @{{ value }}"
    result = parser.parse_directives(template, {"value": "test"})
    assert "Normal: test" in result
    assert "Verbatim: {{ value }}" in result
    
    # Test mixed usage
    template = """
    @verbatim
        @{{ nested.shorthand }}
        {{ regular.syntax }}
    @endverbatim
    """
    result = parser.parse_directives(template, {})
    assert "@{{ nested.shorthand }}" in result
    assert "{{ regular.syntax }}" in result


def test_url_directive():
    """Test URL directive with various features."""
    parser = DirectiveParser()
    
    # Mock Django's reverse function
    class MockReverse:
        def __call__(self, pattern, args=None, kwargs=None):
            if pattern == "user-profile":
                return f"/user/{kwargs.get('id', '')}"
            elif pattern == "search":
                return f"/search?q={kwargs.get('query', '')}"
            return "/"
    
    # Add mock to context
    import sys
    mock_module = type('module', (), {'reverse': MockReverse()})
    sys.modules['django.urls'] = mock_module
    
    # Test basic URL
    template = '@url("user-profile", id=123)'
    result = parser.parse_directives(template, {"urlconf": {}})
    assert result == "/user/123"
    
    # Test URL with multiple parameters
    template = '@url("search", query=search_term)'
    result = parser.parse_directives(template, {
        "urlconf": {},
        "search_term": "test"
    })
    assert result == "/search?q=test"
    
    # Test URL with 'as' variable
    template = '@url("user-profile", id=user_id) as profile_url {{ profile_url }}'
    result = parser.parse_directives(template, {
        "urlconf": {},
        "user_id": 456
    })
    assert "/user/456" in result
    
    # Test error handling
    with pytest.raises(DirectiveParsingError):
        parser.parse_directives('@url("invalid")', {})


def test_component_directive():
    """Test component directive functionality."""
    parser = DirectiveParser()
    
    # Create a test component file
    import os
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.makedirs(os.path.join(temp_dir, "components"))
        component_path = os.path.join(temp_dir, "components/alert.html")
        
        with open(component_path, "w") as f:
            f.write("""
            <div class="{{ type }}">
                <h2>{{ title }}</h2>
                {{ slot }}
            </div>
            """)
        
        # Test basic component usage
        template = """
        @component("alert", type="error", title="Error")
            <p>Something went wrong!</p>
        @endcomponent
        """
        result = parser.parse_directives(template, {})
        assert 'class="error"' in result
        assert "<h2>Error</h2>" in result
        assert "<p>Something went wrong!</p>" in result
        
        # Test component with dynamic data
        template = '@component("alert", type=alert_type, title=alert_title){{ message }}@endcomponent'
        result = parser.parse_directives(template, {
            "alert_type": "success",
            "alert_title": "Great!",
            "message": "Operation completed"
        })
        assert 'class="success"' in result
        assert "<h2>Great!</h2>" in result
        assert "Operation completed" in result


def test_liveblade_scripts_directive():
    """Test liveblade_scripts directive functionality."""
    parser = DirectiveParser()
    
    # Test basic script inclusion
    template = "@liveblade_scripts"
    result = parser.parse_directives(template, {})
    assert '<script src="/static/js/liveblade.js"></script>' in result
    assert "window.liveblade = new Liveblade();" in result
    
    # Test with CSRF token
    template = "@liveblade_scripts"
    result = parser.parse_directives(template, {"csrf_token": "test-token"})
    assert 'content="test-token"' in result
    
    # Test with custom attributes
    template = '@liveblade_scripts(poll_interval=2000, debug="true")'
    result = parser.parse_directives(template, {})
    assert "poll_interval" in result
    assert "2000" in result
    assert "debug" in result
    assert "true" in result


def test_directive_error_handling():
    """Test error handling for all directives."""
    parser = DirectiveParser()
    
    # Test component not found
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives('@component("nonexistent")', {})
    assert "Component not found" in str(exc.value)
    
    # Test invalid URL
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives('@url("invalid")', {})
    assert "URL configuration not found" in str(exc.value)
    
    # Test unclosed verbatim
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives('@verbatim{{ content }}', {})
    assert "Unclosed" in str(exc.value)
    
    # Test invalid component data
    with pytest.raises(DirectiveParsingError) as exc:
        parser.parse_directives('@component("alert", invalid_syntax)', {})
    assert "Error processing component data" in str(exc.value)


def test_style_directive():
    """Test @style directive functionality."""
    parser = DirectiveParser()
    
    # Test basic style
    template = '<div @style({"color: red;": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'style="color: red;"' in result
    
    # Test multiple styles
    template = '<div @style({"color: red;": True, "font-weight: bold;": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'style="color: red; font-weight: bold;"' in result
    
    # Test conditional styles
    context = {"isError": True, "isBold": False}
    template = '<div @style({"color: red;": isError, "font-weight: bold;": isBold})>Test</div>'
    result = parser.parse_directives(template, context)
    assert 'style="color: red;"' in result
    assert 'font-weight: bold' not in result
    
    # Test with expressions
    context = {"count": 5}
    template = '<div @style({"color: red;": count > 3, "color: blue;": count < 3})>Test</div>'
    result = parser.parse_directives(template, context)
    assert 'style="color: red;"' in result
    assert 'color: blue' not in result
    
    # Test empty result when no styles are active
    template = '<div @style({"color: red;": False})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'style=' not in result
    
    # Test style cleanup
    template = '<div @style({"  color: red  ;  ": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'style="color: red;"' in result


def test_style_directive_errors():
    """Test error handling in @style directive."""
    parser = DirectiveParser()
    
    # Test invalid dictionary
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @style("not a dict")>Test</div>'
        parser.parse_directives(template, {})
    assert "requires a dictionary" in str(exc.value)
    
    # Test invalid condition
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @style({"color: red;": "invalid"})>Test</div>'
        parser.parse_directives(template, {})
    assert "Error in @style directive" in str(exc.value)
    
    # Test missing context variable
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @style({"color: red;": undefined_var})>Test</div>'
        parser.parse_directives(template, {})
    assert "Error in @style directive" in str(exc.value)


def test_class_directive():
    """Test @class directive functionality."""
    parser = DirectiveParser()
    
    # Test basic class
    template = '<div @class({"active": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'class="active"' in result
    
    # Test multiple classes
    template = '<div @class({"active": True, "bold": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'class="active bold"' in result
    
    # Test conditional classes
    context = {"isActive": True, "isDisabled": False}
    template = '<div @class({"active": isActive, "disabled": isDisabled})>Test</div>'
    result = parser.parse_directives(template, context)
    assert 'class="active"' in result
    assert 'disabled' not in result
    
    # Test with expressions
    context = {"count": 5}
    template = '<div @class({"highlight": count > 3, "dim": count < 3})>Test</div>'
    result = parser.parse_directives(template, context)
    assert 'class="highlight"' in result
    assert 'dim' not in result
    
    # Test empty result when no classes are active
    template = '<div @class({"active": False})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'class=' not in result
    
    # Test class name cleanup
    template = '<div @class({"  active   ": True})>Test</div>'
    result = parser.parse_directives(template, {})
    assert 'class="active"' in result
    
    # Test with multiple conditions
    context = {"isAdmin": True, "hasErrors": True, "isNew": False}
    template = '''
        <div @class({
            "admin-view": isAdmin,
            "error-state": hasErrors,
            "new-item": isNew
        })>Test</div>
    '''
    result = parser.parse_directives(template, context)
    assert 'admin-view' in result
    assert 'error-state' in result
    assert 'new-item' not in result


def test_class_directive_errors():
    """Test error handling in @class directive."""
    parser = DirectiveParser()
    
    # Test invalid dictionary
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @class("not a dict")>Test</div>'
        parser.parse_directives(template, {})
    assert "requires a dictionary" in str(exc.value)
    
    # Test invalid condition
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @class({"active": "invalid"})>Test</div>'
        parser.parse_directives(template, {})
    assert "Error in @class directive" in str(exc.value)
    
    # Test missing context variable
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @class({"active": undefined_var})>Test</div>'
        parser.parse_directives(template, {})
    assert "Error in @class directive" in str(exc.value)
    
    # Test malformed syntax
    with pytest.raises(DirectiveParsingError) as exc:
        template = '<div @class({active: True)>Test</div>'
        parser.parse_directives(template, {})
    assert "Error in @class directive" in str(exc.value)


def test_include_directive():
    """Test @include directive functionality."""
    parser = DirectiveParser()
    
    # Test basic include
    template = '@include("partials.header")'
    result = parser.parse_directives(template, {})
    # Result will depend on the actual content of partials/header.html
    
    # Test include with data
    template = '@include("components.alert", {"type": "error", "message": "Error!"})'
    result = parser.parse_directives(template, {})
    # Result will include the alert component with the provided data
    
    # Test include with context variables
    context = {"user": {"name": "John"}}
    template = '@include("partials.welcome", {"name": user.name})'
    result = parser.parse_directives(template, context)
    # Result will include the welcome partial with the user's name
    
    # Test nested includes
    template = '@include("layouts.base")'  # base.html includes other partials
    result = parser.parse_directives(template, {})
    # Result will include the base layout with all nested includes


def test_include_directive_errors():
    """Test error handling in @include directive."""
    parser = DirectiveParser()
    
    # Test invalid path format
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@include("invalid/path")'  # Should use dots instead of slashes
        parser.parse_directives(template, {})
    assert "Error in @include directive" in str(exc.value)
    
    # Test missing template
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@include("nonexistent.template")'
        parser.parse_directives(template, {})
    assert "Could not find partial template" in str(exc.value)
    
    # Test invalid data
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@include("partials.header", "invalid")'  # Data should be a dict
        parser.parse_directives(template, {})
    assert "data must be a dictionary" in str(exc.value)
    
    # Test invalid context variable
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@include("partials.header", {"name": undefined_var})'
        parser.parse_directives(template, {})
    assert "Error processing @include data" in str(exc.value)


def test_field_directive():
    """Test @field directive functionality."""
    from django import forms
    
    class TestForm(forms.Form):
        username = forms.CharField(max_length=100, required=True)
        email = forms.EmailField(required=False)
        password = forms.CharField(widget=forms.PasswordInput())
        remember = forms.BooleanField(required=False)
    
    parser = DirectiveParser()
    form = TestForm()
    context = {'form': form}
    
    # Test basic text input with HTML-like attributes
    template = '@field(form.username, class="form-control" placeholder="Enter username" required)'
    result = parser.parse_directives(template, context)
    assert 'type="text"' in result
    assert 'name="username"' in result
    assert 'class="form-control"' in result
    assert 'placeholder="Enter username"' in result
    assert 'required' in result
    
    # Test email input with boolean attributes
    template = '@field(form.email, class="form-control" disabled readonly)'
    result = parser.parse_directives(template, context)
    assert 'type="email"' in result
    assert 'class="form-control"' in result
    assert 'disabled' in result
    assert 'readonly' in result
    assert 'required' not in result
    
    # Test password input with data attributes
    template = '@field(form.password, class="form-control" data-toggle="password" autocomplete="off")'
    result = parser.parse_directives(template, context)
    assert 'type="password"' in result
    assert 'class="form-control"' in result
    assert 'data-toggle="password"' in result
    assert 'autocomplete="off"' in result
    
    # Test checkbox with mixed attributes
    template = '@field(form.remember, class="form-check-input" checked data-toggle="toggle")'
    result = parser.parse_directives(template, context)
    assert 'type="checkbox"' in result
    assert 'class="form-check-input"' in result
    assert 'checked' in result
    assert 'data-toggle="toggle"' in result
    
    # Test with custom id and name
    template = '@field(form.username, id="custom_id" name="custom_name")'
    result = parser.parse_directives(template, context)
    assert 'id="custom_id"' in result
    assert 'name="custom_name"' in result
    
    # Test with field value
    form.initial = {'username': 'testuser'}
    template = '@field(form.username, class="form-control")'
    result = parser.parse_directives(template, {'form': form})
    assert 'value="testuser"' in result
    
    # Test with error class
    form.add_error('username', 'This field is required')
    template = '@field(form.username, class="form-control")'
    result = parser.parse_directives(template, {'form': form})
    assert 'class="form-control is-invalid"' in result


def test_field_directive_errors():
    """Test error handling in field directive."""
    parser = DirectiveParser()
    
    # Test invalid field path
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@field(username, class="form-control")'  # Missing form reference
        parser.parse_directives(template, {})
    assert "Invalid field path" in str(exc.value)
    
    # Test missing form
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@field(nonexistent.field, class="form-control")'
        parser.parse_directives(template, {})
    assert "not found in context" in str(exc.value)
    
    # Test missing field
    from django import forms
    form = forms.Form()
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@field(form.nonexistent, class="form-control")'
        parser.parse_directives(template, {'form': form})
    assert "not found in form" in str(exc.value)
    
    # Test invalid attribute syntax
    with pytest.raises(DirectiveParsingError) as exc:
        template = '@field(form.field, class=form-control)'  # Missing quotes
        parser.parse_directives(template, {'form': forms.Form()})
    assert "Error in @field directive" in str(exc.value)
