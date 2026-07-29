#!/usr/bin/env python
"""Simple test script for form directives"""

import sys
sys.path.insert(0, '/media/antares/Data/coding/backend/pyblade')

from pyblade.engine.processor import TemplateProcessor

def test_directives():
    processor = TemplateProcessor()
    
    # Test @checked
    print("Testing @checked...")
    template = '<input type="checkbox" @checked(checked)>'
    result = processor.render(template, {"checked": True})
    assert "checked" in result, f"Expected 'checked' in result, got: {result}"
    print("✓ @checked with True works")
    
    result = processor.render(template, {"checked": False})
    assert "checked" not in result, f"Expected no 'checked' in result, got: {result}"
    print("✓ @checked with False works")
    
    # Test @selected
    print("\nTesting @selected...")
    template = '<option @selected(selected)>Option</option>'
    result = processor.render(template, {"selected": True})
    assert "selected" in result, f"Expected 'selected' in result, got: {result}"
    print("✓ @selected with True works")
    
    result = processor.render(template, {"selected": False})
    assert "selected" not in result, f"Expected no 'selected' in result, got: {result}"
    print("✓ @selected with False works")
    
    # Test @required
    print("\nTesting @required...")
    template = '<input type="text" @required(required)>'
    result = processor.render(template, {"required": True})
    assert "required" in result, f"Expected 'required' in result, got: {result}"
    print("✓ @required with True works")
    
    result = processor.render(template, {"required": False})
    assert "required" not in result, f"Expected no 'required' in result, got: {result}"
    print("✓ @required with False works")
    
    # Test @field
    print("\nTesting @field...")
    template = '<input type="text" value="@field(\'username\', \'guest\')">'
    result = processor.render(template, {"username": "john"})
    assert 'value="john"' in result, f"Expected 'value=\"john\"' in result, got: {result}"
    print("✓ @field with context value works")
    
    result = processor.render(template, {})
    assert 'value="guest"' in result, f"Expected 'value=\"guest\"' in result, got: {result}"
    print("✓ @field with default value works")
    
    # Test @field with old input
    print("\nTesting @field with old input...")
    template = '<input type="text" value="@field(\'email\')">'
    context = {
        "_old": {"email": "old@example.com"},
        "email": "current@example.com"
    }
    result = processor.render(template, context)
    assert 'value="old@example.com"' in result, f"Expected 'value=\"old@example.com\"' in result, got: {result}"
    print("✓ @field with old input priority works")
    
    # Test @field with model
    print("\nTesting @field with model...")
    class User:
        def __init__(self):
            self.name = "Model User"
    
    template = '<input type="text" value="@field(\'name\')">'
    result = processor.render(template, {"model": User()})
    assert 'value="Model User"' in result, f"Expected 'value=\"Model User\"' in result, got: {result}"
    print("✓ @field with model binding works")
    
    print("\n✅ All form directive tests passed!")

if __name__ == "__main__":
    test_directives()
