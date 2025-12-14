
import pytest
from pyblade.engine.processor import TemplateProcessor
from pyblade.engine.exceptions import TemplateRenderError

def test_unless_directive():
    processor = TemplateProcessor()
    template = "@unless(condition)Show this@endunless"
    
    assert processor.render(template, {"condition": False}) == "Show this"
    assert processor.render(template, {"condition": True}) == ""

def test_switch_directive():
    processor = TemplateProcessor()
    template = """
    @switch(value)
        @case(1)
            One
        @case(2)
            Two
        @default
            Other
    @endswitch
    """
    
    assert processor.render(template, {"value": 1}).strip() == "One"
    assert processor.render(template, {"value": 2}).strip() == "Two"
    assert processor.render(template, {"value": 3}).strip() == "Other"

def test_auth_guest_directives():
    processor = TemplateProcessor()
    
    class User:
        is_authenticated = True
        
    class AnonymousUser:
        is_authenticated = False
        
    template_auth = "@auth Authenticated @else Guest @endauth"
    template_guest = "@guest Guest @else Authenticated @endguest"
    
    # Test authenticated
    context = {"user": User()}
    assert processor.render(template_auth, context).strip() == "Authenticated"
    assert processor.render(template_guest, context).strip() == "Authenticated"
    
    # Test guest
    context = {"user": AnonymousUser()}
    assert processor.render(template_auth, context).strip() == "Guest"
    assert processor.render(template_guest, context).strip() == "Guest"

def test_verbatim_directive():
    processor = TemplateProcessor()
    template = "@verbatim {{ raw }} @endverbatim"
    assert processor.render(template, {}).strip() == "{{ raw }}"

def test_cycle_directive():
    processor = TemplateProcessor()
    template = "@for(i in range(3))@cycle('odd', 'even') @endfor"
    assert processor.render(template, {}).strip() == "odd even odd"

def test_firstof_directive():
    processor = TemplateProcessor()
    template = "@firstof(a, b, 'default')"
    assert processor.render(template, {"a": None, "b": "B"}) == "B"
    assert processor.render(template, {"a": None, "b": None}) == "default"

def test_style_class_directives():
    processor = TemplateProcessor()
    
    template_style = '<div @style({"color: red": True, "display: none": False})></div>'
    assert 'style="color: red"' in processor.render(template_style, {})
    
    template_class = '<div @class({"active": True, "hidden": False})></div>'
    assert 'class="active"' in processor.render(template_class, {})

def test_break_continue():
    processor = TemplateProcessor()
    
    template_break = "@for(i in range(5)){{ i }}@break(i==2)@endfor"
    assert processor.render(template_break, {}) == "012"
    
    template_continue = "@for(i in range(5))@continue(i==2){{ i }}@endfor"
    assert processor.render(template_continue, {}) == "0134"
