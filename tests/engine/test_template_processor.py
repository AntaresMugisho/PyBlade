"""Tests for the template processor."""
import pytest
from pyblade.engine.parsing.template_processor import TemplateProcessor
from pyblade.engine.exceptions import TemplateRenderingError


def test_render_simple_template():
    """Test rendering a simple template with variables."""
    processor = TemplateProcessor()
    template = "Hello, {{ name }}!"
    context = {"name": "World"}
    
    result = processor.render(template, context)
    assert result == "Hello, World!"


def test_render_with_html_escaping():
    """Test that HTML is properly escaped by default."""
    processor = TemplateProcessor()
    template = "{{ content }}"
    context = {"content": "<script>alert('xss')</script>"}
    
    result = processor.render(template, context)
    assert result == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"


def test_render_with_unescaped_html():
    """Test that HTML can be rendered unescaped when explicitly requested."""
    processor = TemplateProcessor()
    template = "{!! content !!}"
    context = {"content": "<strong>bold</strong>"}
    
    result = processor.render(template, context)
    assert result == "<strong>bold</strong>"


def test_render_with_conditional():
    """Test rendering with @if directive."""
    processor = TemplateProcessor()
    template = "@if(show)Hello@endif"
    
    result = processor.render(template, {"show": True})
    assert result == "Hello"
    
    result = processor.render(template, {"show": False})
    assert result == ""


def test_render_with_loop():
    """Test rendering with @for directive."""
    processor = TemplateProcessor()
    template = "@for(item in items){{ item }}@endfor"
    context = {"items": ["a", "b", "c"]}
    
    result = processor.render(template, context)
    assert result == "abc"


def test_render_with_nested_variables():
    """Test rendering with nested object attributes."""
    processor = TemplateProcessor()
    template = "{{ user.get('name') }}"
    context = {"user": {"name": "John"}}
    
    result = processor.render(template, context)
    assert result == "John"


def test_render_with_undefined_variable():
    """Test that undefined variables raise an error."""
    processor = TemplateProcessor()
    template = "{{ undefined }}"
    
    with pytest.raises(TemplateRenderingError):
        processor.render(template, {})


def test_template_caching():
    """Test that templates are properly cached."""
    processor = TemplateProcessor(cache_size=1)
    template = "Hello, {{ name }}!"
    context = {"name": "World"}
    
    # First render should cache the result
    result1 = processor.render(template, context)
    
    # Second render should use cache
    result2 = processor.render(template, context)
    
    assert result1 == result2
    assert processor.cache.size == 1


def test_cache_invalidation():
    """Test that cache invalidation works."""
    processor = TemplateProcessor()
    template = "Hello, {{ name }}!"
    context = {"name": "World"}
    
    # Cache the template
    processor.render(template, context)
    assert processor.cache.size == 1
    
    # Invalidate the cache
    processor.invalidate_template(template, context)
    assert processor.cache.size == 0


def test_cache_size_limit():
    """Test that cache size limit is respected."""
    processor = TemplateProcessor(cache_size=2)
    
    # Add three templates to cache
    processor.render("1{{ var }}", {"var": "a"})
    processor.render("2{{ var }}", {"var": "b"})
    processor.render("3{{ var }}", {"var": "c"})
    
    # Cache should only contain 2 items
    assert processor.cache.size == 2
