import datetime
import unittest

from pyblade.engine.exceptions import DirectiveParsingError
from pyblade.engine.processor import TemplateProcessor



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

    def test_section_yield_inheritance(self):
        # Test @section and @yield directives (Laravel Blade style)
        template = """
        @section('content')
            <p>This is the content</p>
        @endsection
        """
        # The section should be stored in context but not rendered directly
        result = self._render(template)
        self.assertEqual(result.strip(), "")

    def test_block_inheritance(self):
        # Test @block directive
        template = """
        @block('header')
            <h1>Default Header</h1>
        @endblock
        """
        result = self._render(template)
        self.assertIn("Default Header", result)

    def test_yield_with_default(self):
        # Test @yield with default value
        template = "@yield('missing_section', 'Default Content')"
        result = self._render(template)
        self.assertEqual(result.strip(), "Default Content")

    def test_checked_directive(self):
        # Test @checked directive
        template = '<input type="checkbox" @checked(checked)>'
        result = self._render(template, {"checked": True})
        self.assertIn("checked", result)
        
        result = self._render(template, {"checked": False})
        self.assertNotIn("checked", result)

    def test_selected_directive(self):
        # Test @selected directive
        template = '<option @selected(selected)>Option</option>'
        result = self._render(template, {"selected": True})
        self.assertIn("selected", result)
        
        result = self._render(template, {"selected": False})
        self.assertNotIn("selected", result)

    def test_required_directive(self):
        # Test @required directive
        template = '<input type="text" @required(required)>'
        result = self._render(template, {"required": True})
        self.assertIn("required", result)
        
        result = self._render(template, {"required": False})
        self.assertNotIn("required", result)

    def test_field_directive(self):
        # Test @field directive with attributes (django-widget-tweaks style)
        # Mock Django form field
        class MockField:
            def __str__(self):
                return '<input type="text" name="username" id="id_username">'
        
        template = '@field(form.username, class="form-control", placeholder="Enter username")'
        result = self._render(template, {"form": {"username": MockField()}})
        self.assertIn('class="form-control"', result)
        self.assertIn('placeholder="Enter username"', result)

    def test_field_with_append_attribute(self):
        # Test @field directive with append syntax (class+="value")
        class MockField:
            def __str__(self):
                return '<input type="text" name="email" class="default-class" id="id_email">'
        
        template = '@field(form.email, class+="extra-class")'
        result = self._render(template, {"form": {"email": MockField()}})
        self.assertIn('extra-class', result)
        self.assertIn('default-class', result)

    def test_error_directive_with_django_form(self):
        # Test @error directive with Django-style form errors
        class MockForm:
            def __init__(self):
                self.errors = {"email": ["This field is required."]}
        
        template = """
        @error(form.email)
            <small class="text-red-500">{{ message }}</small>
        @enderror
        """
        result = self._render(template, {"form": MockForm()})
        self.assertIn("This field is required.", result)
        self.assertIn("text-red-500", result)

    def test_error_directive_with_laravel_errors(self):
        # Test @error directive with Laravel-style errors bag
        template = """
        @error(form.email)
            <small class="text-red-500">{{ message }}</small>
        @enderror
        """
        result = self._render(template, {"errors": {"email": "Invalid email format"}})
        self.assertIn("Invalid email format", result)
        self.assertIn("text-red-500", result)

    def test_error_directive_no_errors(self):
        # Test @error directive when no errors exist
        template = """
        @error(form.email)
            <small class="text-red-500">{{ message }}</small>
        @enderror
        """
        result = self._render(template, {"form": {}, "errors": {}})
        self.assertEqual(result.strip(), "")

    def test_pb_self_closing_component(self):
        # Test self-closing pb- component tag
        template = '<pb-button label="Click me" />'
        result = self._render(template, {})
        # Should render as component (empty result if component doesn't exist)
        self.assertIsInstance(result, str)

    def test_pb_paired_component_with_content(self):
        # Test paired pb- component tag with content
        template = '<pb-alert type="error">Error message here</pb-alert>'
        result = self._render(template, {})
        # Should render as component with slot content
        self.assertIsInstance(result, str)

    def test_pb_component_with_multiple_attributes(self):
        # Test pb- component with multiple attributes
        template = '<pb-input type="text" placeholder="Enter name" required=true />'
        result = self._render(template, {})
        self.assertIsInstance(result, str)

    def test_pb_nested_components(self):
        # Test nested pb- components
        template = '<pb-card><pb-button label="Click" /></pb-card>'
        result = self._render(template, {})
        self.assertIsInstance(result, str)

    def test_autofocus_directive(self):
        # Test @autofocus directive
        template = '<input type="text" @autofocus(should_focus)>'
        result = self._render(template, {"should_focus": True})
        self.assertIn("autofocus", result)
        
        result = self._render(template, {"should_focus": False})
        self.assertNotIn("autofocus", result)

    def test_multiple_directive(self):
        # Test @multiple directive
        template = '<select @multiple(allow_multiple)>'
        result = self._render(template, {"allow_multiple": True})
        self.assertIn("multiple", result)
        
        result = self._render(template, {"allow_multiple": False})
        self.assertNotIn("multiple", result)

    def test_readonly_directive(self):
        # Test @readonly directive
        template = '<input type="text" @readonly(is_readonly)>'
        result = self._render(template, {"is_readonly": True})
        self.assertIn("readonly", result)
        
        result = self._render(template, {"is_readonly": False})
        self.assertNotIn("readonly", result)

    def test_disabled_directive(self):
        # Test @disabled directive
        template = '<button @disabled(is_disabled)>Click</button>'
        result = self._render(template, {"is_disabled": True})
        self.assertIn("disabled", result)
        
        result = self._render(template, {"is_disabled": False})
        self.assertNotIn("disabled", result)


class TestAttributeDirectives(unittest.TestCase):
    """@checked, @selected, @disabled and the like, which render an HTML attribute."""

    ATTRIBUTES = ("checked", "selected", "disabled", "readonly", "required", "multiple", "autofocus")

    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    def test_without_parentheses_the_attribute_is_rendered(self):
        for attribute in self.ATTRIBUTES:
            with self.subTest(attribute=attribute):
                self.assertEqual(self._render(f"<input@{attribute}>"), f"<input {attribute}>")

    def test_with_an_expression_the_attribute_follows_it(self):
        for attribute in self.ATTRIBUTES:
            with self.subTest(attribute=attribute):
                template = f"<input@{attribute}(condition)>"

                self.assertEqual(self._render(template, {"condition": True}), f"<input {attribute}>")
                self.assertEqual(self._render(template, {"condition": False}), "<input>")

    def test_inside_a_loop(self):
        template = "@for(option in options)<option@selected(option == current)>{{ option }}</option>@endfor"

        result = self._render(template, {"options": ["a", "b"], "current": "b"})

        self.assertEqual(result, "<option>a</option><option selected>b</option>")

    def test_inside_a_condition(self):
        template = "@if(show)<input@disabled(locked)>@endif"

        self.assertEqual(self._render(template, {"show": True, "locked": True}), "<input disabled>")
        self.assertEqual(self._render(template, {"show": True, "locked": False}), "<input>")

    def test_inside_a_condition_without_parentheses(self):
        self.assertEqual(self._render("@if(show)<input@checked>@endif", {"show": True}), "<input checked>")


class TestDirectivesInsideBlocks(unittest.TestCase):
    """Directives must be parsed the same way wherever they appear."""

    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    def test_directive_taking_arguments_inside_a_loop(self):
        template = "@for(item in items)@now('%Y') {{ item }}@endfor"

        result = self._render(template, {"items": ["a"]})

        self.assertIn("a", result)
        self.assertNotIn("@now", result)

    def test_unknown_directive_inside_a_loop_is_left_as_text(self):
        template = "@for(item in items)@unknown {{ item }}@endfor"

        self.assertEqual(self._render(template, {"items": ["a"]}), "@unknown a")

    def test_misplaced_closing_directive_inside_a_loop_is_reported(self):
        with self.assertRaises(DirectiveParsingError):
            self._render("@for(item in items)@endif@endfor", {"items": ["a"]})


if __name__ == "__main__":
    unittest.main()
