import unittest
from pyblade.engine.parser import Parser
from pyblade.engine.parser import Parser
from pyblade.engine.processor import TemplateProcessor
from pyblade.engine.nodes import *

class TestPhase2Directives(unittest.TestCase):
    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

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
        <div @ratio(16, 9)></div>
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
        self.assertIn('style="aspect-ratio: 16/9;"', output)

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
