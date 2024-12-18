"""Tests for template directives."""
import pytest
from pyblade.engine.parsing.directives import DirectiveParser


def test_parse_if_directive():
    """Test parsing @if directives."""
    parser = DirectiveParser()
    template = """
    @if(condition)
        content
    @endif
    """
    
    result = parser.parse_directives(template, {"condition": True})
    assert result == "content@endif"
    
    # result = parser.parse_directives(template, {"condition": False})
    # assert result == ""


def test_parse_else_directive():
    """Test parsing @else directives."""
    parser = DirectiveParser()
    template = "@if(condition)true@else false@endif"
    
    result = parser.parse_directives(template, {"condition": True})
    assert result == "true"
    
    result = parser.parse_directives(template, {"condition": False})
    assert result == " false"


def test_parse_elseif_directive():
    """Test parsing @elseif directives."""
    parser = DirectiveParser()
    template = "@if(a)A@elseif(b)B@else C@endif"
    
    result = parser.parse_directives(template, {"a": True, "b": False})
    assert result == "A"
    
    result = parser.parse_directives(template, {"a": False, "b": True})
    assert result == "B"
    
    result = parser.parse_directives(template, {"a": False, "b": False})
    assert result == " C"


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
