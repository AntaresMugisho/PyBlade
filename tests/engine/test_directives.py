import sys
from unittest.mock import MagicMock
sys.modules["questionary"] = MagicMock()

import unittest
from pyblade.engine.parser import Parser
from pyblade.engine.processor import TemplateProcessor
from pyblade.engine.nodes import *

class TestPhase2Directives(unittest.TestCase):
    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    def test_unless_directive(self):
        template = "@unless(condition)Show this@endunless"
        
        assert self._render(template, {"condition": False}) == "Show this"
        assert self._render(template, {"condition": True}) == ""

    def test_switch_directive(self):
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
        assert self._render(template, {"value": 1}).strip() == "One"
        assert self._render(template, {"value": 2}).strip() == "Two"
        assert self._render(template, {"value": 3}).strip() == "Other"

    def test_auth_guest_directives(self):
        
        class User:
            is_authenticated = True
            
        class AnonymousUser:
            is_authenticated = False
            
        template_auth = "@auth Authenticated @else Guest @endauth"
        template_guest = "@guest Guest @else Authenticated @endguest"
        
        context = {"user": User()}
        assert self._render(template_auth, context).strip() == "Authenticated"
        assert self._render(template_guest, context).strip() == "Authenticated"
        
        # Test guest
        context = {"user": AnonymousUser()}
        assert self._render(template_auth, context).strip() == "Guest"
        assert self._render(template_guest, context).strip() == "Guest"

    def test_verbatim_directive(self):
        template = "@verbatim {{ raw }} @endverbatim"
        assert self._render(template, {}).strip() == "{{ raw }}"

    def test_cycle_directive(self):
        template = "@for(i in range(3))@cycle('odd', 'even') @endfor"
        assert self._render(template, {}).strip() == "odd even odd"

    def test_firstof_directive(self):
        template = "@firstof(a, b, 'default')"
        assert self._render(template, {"a": None, "b": "B"}) == "B"
        assert self._render(template, {"a": None, "b": None}) == "default"

    def test_style_class_directives(self):
        template_style = '<div @style({"color: red": True, "display: none": False})></div>'
        assert 'style="color: red"' in self._render(template_style, {})
        
        template_class = '<div @class({"active": True, "hidden": False})></div>'
        assert 'class="active"' in self._render(template_class, {})

    def test_break_continue(self):        
        template_break = "@for(i in range(5)){{ i }}@break(i==2)@endfor"
        assert self._render(template_break, {}) == "012"
        
        template_continue = "@for(i in range(5))@continue(i==2){{ i }}@endfor"
        assert self._render(template_continue, {}) == "0134"


    def test_trans(self):
        template = "@trans('Hello')"
        self.assertEqual(self._render(template), "Hello")

    def test_blocktranslate(self):
        template = "@blocktranslate\nHello {{ name }}\n@endblocktranslate"
        self.assertEqual(self._render(template, {"name": "World"}).strip(), "Hello World")

    def test_with(self):
        template = "@with(a=1, b=2)\n{{ a }} + {{ b }} = {{ a + b }}\n@endwith"
        self.assertEqual(self._render(template).strip(), "1 + 2 = 3")

    def test_now(self):
        # Mock datetime? Or just check format.
        # We can't easily mock datetime inside processor without injection.
        # Let's just check it returns something non-empty and formatted.
        template = "@now('%Y')"
        import datetime
        year = datetime.datetime.now().strftime('%Y')
        self.assertEqual(self._render(template), year)

    def test_regroup(self):
        cities = [
            {'name': 'Mumbai', 'population': '19,000,000', 'country': 'India'},
            {'name': 'Calcutta', 'population': '15,000,000', 'country': 'India'},
            {'name': 'New York', 'population': '20,000,000', 'country': 'USA'},
            {'name': 'Chicago', 'population': '7,000,000', 'country': 'USA'},
            {'name': 'Tokyo', 'population': '33,000,000', 'country': 'Japan'},
        ]
        # Regroup by country
        template = """
        @regroup(cities by country as country_list)
        @for(country in country_list)
            {{ country.grouper }}
            @for(city in country.list)
                {{ city.name }}
            @endfor
        @endfor
        """
        output = self._render(template, {"cities": cities})
        self.assertIn("India", output)
        self.assertIn("Mumbai", output)
        self.assertIn("Calcutta", output)
        self.assertIn("USA", output)
        self.assertIn("New York", output)
        self.assertIn("Japan", output)

    def test_form_directives(self):
        template = """
        <input @selected(is_selected)>
        <input @required(is_required)>
        <input @checked(is_checked)>
        <input @autocomplete(auto_val)>
        """
        context = {
            "is_selected": True,
            "is_required": False,
            "is_checked": True,
            "auto_val": "off"
        }
        output = self._render(template, context)
        self.assertIn("selected", output)
        self.assertNotIn("required", output)
        self.assertIn("checked", output)
        self.assertIn('autocomplete="off"', output)

    def test_url_helpers(self):
        template = """
        @get_static_prefix
        @get_media_prefix
        """
        output = self._render(template)
        self.assertIn("/static/", output)
        self.assertIn("/media/", output)

    def test_querystring(self):
        # Mock request in context
        class MockRequest:
            class GET:
                def copy(self): return self
                def dict(self): return {'page': '1', 'sort': 'asc'}
            GET = GET()
        
        context = {'request': MockRequest()}
        template = "@querystring(page=2)"
        output = self._render(template, context)
        self.assertIn("page=2", output)
        self.assertIn("sort=asc", output)

    def test_inline_comment(self):
        template = "Hello {# This is a comment #} World"
        self.assertEqual(self._render(template).strip(), "Hello  World")

    def test_block_inheritance(self):
        # This is hard to test without file system.
        # But we can test @block behavior in single file?
        # Or mock file loading.
        # Let's test basic block rendering.
        template = "@block('header')Default Header@endblock"
        self.assertEqual(self._render(template), "Default Header")
        
        # Test override if we manually populate blocks (simulating inheritance)
        # But processor.render resets context? No, we pass context.
        context = {'__blocks': {'header': 'New Header'}}
        self.assertEqual(self._render(template, context), "New Header")

if __name__ == '__main__':
    unittest.main()
