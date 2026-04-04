import datetime
import sys
import unittest
from unittest.mock import MagicMock

from pyblade.engine.processor import TemplateProcessor

sys.modules["questionary"] = MagicMock()
sys.modules["django.conf"] = MagicMock()
sys.modules["django.conf"].settings.STATIC_URL = "/static/"
sys.modules["django.conf"].settings.MEDIA_URL = "/media/"
sys.modules["django.urls"] = MagicMock()
sys.modules["django.utils"] = MagicMock()
sys.modules["django.utils.translation"] = MagicMock()
sys.modules["django.utils.translation"].gettext_lazy = lambda x: x
sys.modules["django.utils.translation"].pgettext = lambda c, m: m


class TestDirectives(unittest.TestCase):
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

        template_as = "@cycle('odd', 'even' as row_class silent)@for(i in range(3)){{ row_class }} @endfor"
        assert self._render(template_as, {}).strip() == "odd even odd"

        template_as_advance = "@cycle('X', 'Y', 'Z' as letters silent)@for(i in range(4)){{ letters }} @endfor"
        assert self._render(template_as_advance, {}).strip() == "X Y Z X"

        template_reset = "@cycle('1', '2' as numbers) @resetcycle(numbers)@cycle(numbers)"
        assert self._render(template_reset, {}).strip() == "1 1"

        template_normal_advance = "@cycle('odd', 'even' as class_name) @cycle(class_name)"
        assert self._render(template_normal_advance, {}).strip() == "odd even"

    def test_firstof_directive(self):
        template = "@firstof(a, b, 'default')"
        assert self._render(template, {"a": None, "b": "B"}) == "B"
        assert self._render(template, {"a": None, "b": None}) == "default"

        template_as = "@firstof(a, b, 'fallback' as myvar){{ myvar }}"
        assert self._render(template_as, {"a": None, "b": None}) == "fallback"

    def test_ifchanged_directive(self):
        template = "@for(i in items)@ifchanged(i){{ i }}@else Same @endifchanged@endfor"
        assert self._render(template, {"items": [1, 1, 2, 2, 3]}) == "1 Same 2 Same 3"

        template_noargs = "@for(i in items)@ifchanged{{ i }}@else Same @endifchanged@endfor"
        assert self._render(template_noargs, {"items": [1, 1, 2, 2, 3]}) == "1 Same 2 Same 3"

    @unittest.skip("Pre-existing bug in _parse_args handling dict literals")
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

    @unittest.skip("Not implemented")
    def test_blocktranslate(self):
        template = "@blocktranslate\nHello {{ name }}\n@endblocktranslate"
        self.assertEqual(self._render(template, {"name": "World"}).strip(), "Hello World")

    def test_with(self):
        template = "@with(a=1, b=2)\n{{ a }} + {{ b }} = {{ a + b }}\n@endwith"
        self.assertEqual(self._render(template).strip(), "1 + 2 = 3")

    def test_now(self):
        template = "@now('%Y')"
        template_as = "@now('%Y' as current_year)Year: {{ current_year }}"

        year = datetime.datetime.now().strftime("%Y")
        self.assertEqual(self._render(template), year)
        self.assertEqual(self._render(template_as), f"Year: {year}")

    def test_regroup(self):
        cities = [
            {"name": "Mumbai", "population": "19,000,000", "country": "India"},
            {"name": "Calcutta", "population": "15,000,000", "country": "India"},
            {"name": "New York", "population": "20,000,000", "country": "USA"},
            {"name": "Chicago", "population": "7,000,000", "country": "USA"},
            {"name": "Tokyo", "population": "33,000,000", "country": "Japan"},
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
        context = {"is_selected": True, "is_required": False, "is_checked": True, "auto_val": "off"}
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

    def test_ratio(self):
        template = """
        <p>Project Completion: @ratio((60), 120, 100) %</p>
        """

        output = self._render(template)
        self.assertIn("50", output)

    def test_querystring(self):
        # Mock request in context
        class MockRequest:
            class GET:
                def copy(self):
                    return self

                def dict(self):
                    return {"page": "1", "sort": "asc"}

            GET = GET()

        context = {"request": MockRequest()}
        template = "@querystring(page=2)"
        output = self._render(template, context)
        self.assertIn("page=2", output)
        self.assertIn("sort=asc", output)

    def test_inline_comment(self):
        template = "Hello {# This is a comment #} World"
        self.assertEqual(self._render(template).strip(), "Hello  World")


if __name__ == "__main__":
    unittest.main()
