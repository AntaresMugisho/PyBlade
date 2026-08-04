import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateRenderError
from pyblade.engine.lexer import Lexer
from pyblade.engine.parser import Parser
from pyblade.engine.processor import TemplateProcessor


class ComponentTestCase(unittest.TestCase):
    def setUp(self):
        self.templates_dir = Path(tempfile.mkdtemp())
        self.components_dir = self.templates_dir / "components"
        self.components_dir.mkdir()

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.templates_dir])

        self._saved_components_dir = settings._data.get("components_dir")
        settings._data["components_dir"] = str(self.components_dir)

        self.processor = TemplateProcessor()

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        if self._saved_components_dir is None:
            settings._data.pop("components_dir", None)
        else:
            settings._data["components_dir"] = self._saved_components_dir
        shutil.rmtree(self.templates_dir, ignore_errors=True)

    def _component(self, name, content):
        """Write a component template, `name` using dot notation (e.g. 'nav.link')."""
        return self._write(name, content, directory=self.components_dir)

    def _write(self, name, content, directory=None):
        path = (directory or self.templates_dir) / f"{name.replace('.', '/')}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    def _parse(self, template):
        return Parser(Lexer(template).tokenize()).parse()


class TestComponentTags(ComponentTestCase):
    """<pb-*> tags, their attributes and the @component directive."""

    def test_self_closing_component(self):
        self._component("user_profile", "<div>Profile</div>")

        self.assertEqual(self._render("<pb-user-profile />"), "<div>Profile</div>")

    def test_component_in_a_subfolder_with_dot_notation(self):
        self._component("nav.link", '<a href="{{ href }}">{{ label }}</a>')

        result = self._render('<pb-nav.link href="/" label="Home" />')

        self.assertEqual(result, '<a href="/">Home</a>')

    def test_component_directive_still_works(self):
        self._component("nav.link", '<a href="{{ href }}">{{ label }}</a>')

        result = self._render('@component("nav.link", {"href": "/", "label": "Home"})')

        self.assertEqual(result, '<a href="/">Home</a>')

    def test_attributes_become_props(self):
        self._component("button", '<button type="{{ type }}">{{ label }}</button>')

        result = self._render('<pb-button type="primary" label="Go" />')

        self.assertEqual(result, '<button type="primary">Go</button>')

    def test_valueless_attribute_is_a_true_prop(self):
        # @disabled renders its own leading space, hence no space before it
        self._component("button", '@props({"disabled": False})<button@disabled(disabled)>Go</button>')

        self.assertEqual(self._render("<pb-button disabled />"), "<button disabled>Go</button>")
        self.assertEqual(self._render("<pb-button />"), "<button>Go</button>")

    def test_unquoted_attribute_is_an_expression(self):
        self._component("button", "<button>{{ label }}</button>")

        result = self._render("<pb-button label=title />", {"title": "From context"})

        self.assertEqual(result, "<button>From context</button>")

    def test_paired_component_content_becomes_the_default_slot(self):
        self._component("card", '<div class="card">{{ slot }}</div>')

        self.assertEqual(self._render("<pb-card>Content</pb-card>"), '<div class="card">Content</div>')

    def test_component_template_must_have_a_single_root_node(self):
        self._component("broken", "<h1>Title</h1><p>Content</p>")

        with self.assertRaises(TemplateRenderError) as raised:
            self._render("<pb-broken />")

        self.assertIn("single root node", raised.exception.message)


class TestComponentProps(ComponentTestCase):
    """@props inside component templates."""

    ALERT = '@props({"type": "info", "message": "Nothing"})<div class="{{ type }}">{{ message }}</div>'

    def test_props_define_default_values(self):
        self._component("alert", self.ALERT)

        self.assertEqual(self._render("<pb-alert />"), '<div class="info">Nothing</div>')

    def test_passed_attributes_override_props_defaults(self):
        self._component("alert", self.ALERT)

        result = self._render('<pb-alert type="error" message="Boom" />')

        self.assertEqual(result, '<div class="error">Boom</div>')

    def test_attributes_bag_is_not_escaped(self):
        self._component("alert", '@props({"type": "info"})<div class="{{ type }}"{{ attributes }}>Body</div>')

        result = self._render('<pb-alert type="error" id="main" />')

        self.assertEqual(result, '<div class="error" id="main">Body</div>')

    def test_attribute_values_are_escaped_in_the_attributes_bag(self):
        self._component("alert", "<div{{ attributes }}>Body</div>")

        result = self._render("<pb-alert id=untrusted />", {"untrusted": '"><script>'})

        self.assertEqual(result, '<div id="&quot;&gt;&lt;script&gt;">Body</div>')

    def test_valueless_attribute_is_spread_as_a_bare_attribute(self):
        self._component("alert", "<div{{ attributes }}>Body</div>")

        self.assertEqual(self._render("<pb-alert disabled />"), "<div disabled>Body</div>")
        self.assertEqual(self._render("<pb-alert disabled=False />"), "<div>Body</div>")

    def test_props_are_left_out_of_the_attributes_bag(self):
        self._component("alert", '@props({"type": "info"})<div class="{{ type }}"{!! attributes !!}>Body</div>')

        result = self._render('<pb-alert type="error" id="main" />')

        self.assertEqual(result, '<div class="error" id="main">Body</div>')

    def test_props_directive_outputs_nothing_of_its_own(self):
        self._component("alert", '@props({"type": "info"})<div>{{ type }}</div>')

        self.assertEqual(self._render("<pb-alert />"), "<div>info</div>")

    def test_undeclared_variable_is_reported_against_the_component_file(self):
        component = self._component("card", "<div>\n    {{ missing }}\n</div>")

        with self.assertRaises(TemplateRenderError) as raised:
            self._render("<h1>Home</h1>\n<pb-card />")

        self.assertEqual(raised.exception.template.path, component)
        self.assertEqual(raised.exception.line, 2)

    def test_error_in_slot_content_is_reported_against_the_calling_file(self):
        self._component("card", "<div>{{ slot }}</div>")

        with self.assertRaises(TemplateRenderError) as raised:
            self._render("<h1>Home</h1>\n<pb-card>{{ missing }}</pb-card>")

        # No template means the one being rendered, which is where the slot is written
        self.assertIsNone(raised.exception.template)
        self.assertEqual(raised.exception.line, 2)

    def test_props_can_be_declared_over_several_lines(self):
        self._component(
            "alert",
            '@props({\n    "type": "info",\n    "message": "Nothing"\n})\n<div class="{{ type }}">{{ message }}</div>',
        )

        self.assertEqual(self._render("<pb-alert />").strip(), '<div class="info">Nothing</div>')

    def test_props_directive_requires_a_dictionary(self):
        self._component("alert", '@props("info")<div>Body</div>')

        with self.assertRaises(TemplateRenderError) as raised:
            self._render("<pb-alert />")

        self.assertIn("@props", raised.exception.message)


class TestSlots(ComponentTestCase):
    """The three slot syntaxes, all normalized into the same representation."""

    LAYOUT = "<div><h1>{{ title }}</h1><main>{{ slot }}</main></div>"

    def test_named_slot_with_the_slot_directive(self):
        self._component("layout", self.LAYOUT)

        result = self._render("<pb-layout>@slot('title')Dashboard@endslot<p>Body</p></pb-layout>")

        self.assertEqual(result, "<div><h1>Dashboard</h1><main><p>Body</p></main></div>")

    def test_slot_directive_without_a_name_fills_the_default_slot(self):
        self._component("card", "<div>{{ slot }}</div>")

        self.assertEqual(self._render("<pb-card>@slot Content @endslot</pb-card>"), "<div>Content</div>")

    def test_named_slot_with_a_pb_slot_tag(self):
        self._component("layout", self.LAYOUT)

        result = self._render('<pb-layout><pb-slot name="title">Dashboard</pb-slot><p>Body</p></pb-layout>')

        self.assertEqual(result, "<div><h1>Dashboard</h1><main><p>Body</p></main></div>")

    def test_named_slot_with_the_shorthand_tag(self):
        self._component("layout", self.LAYOUT)

        result = self._render("<pb-layout><pb-slot:title>Dashboard</pb-slot:title><p>Body</p></pb-layout>")

        self.assertEqual(result, "<div><h1>Dashboard</h1><main><p>Body</p></main></div>")

    def test_shorthand_slot_accepts_the_short_closing_tag(self):
        self._component("layout", self.LAYOUT)

        result = self._render("<pb-layout><pb-slot:title>Dashboard</pb-slot><p>Body</p></pb-layout>")

        self.assertEqual(result, "<div><h1>Dashboard</h1><main><p>Body</p></main></div>")

    def test_every_slot_syntax_gives_the_same_representation(self):
        templates = (
            "<pb-layout>@slot('title')Dashboard@endslot</pb-layout>",
            '<pb-layout><pb-slot name="title">Dashboard</pb-slot></pb-layout>',
            "<pb-layout><pb-slot:title>Dashboard</pb-slot:title></pb-layout>",
            "<pb-layout><pb-slot:title>Dashboard</pb-slot></pb-layout>",
        )

        representations = {repr(self._parse(template)[0].slots["title"]) for template in templates}

        self.assertEqual(len(representations), 1)

    def test_content_outside_named_slots_becomes_the_default_slot(self):
        self._component("layout", self.LAYOUT)

        template = """<pb-layout>
            <pb-slot name="title">Dashboard</pb-slot>
            <main>Content</main>
        </pb-layout>"""

        self.assertEqual(self._render(template), "<div><h1>Dashboard</h1><main><main>Content</main></main></div>")

    def test_slot_keeps_template_nodes_instead_of_rendered_html(self):
        nodes = self._parse("<pb-card>Hello {{ user.name }}</pb-card>")

        slot_nodes = nodes[0].slots["slot"].nodes

        self.assertEqual([type(node).__name__ for node in slot_nodes], ["TextNode", "VarNode"])

    def test_slot_is_rendered_in_the_context_of_the_caller(self):
        self._component("card", "<div>{{ slot }}</div>")

        result = self._render("<pb-card>Hello {{ user.name }}</pb-card>", {"user": {"name": "Antares"}})

        self.assertEqual(result, "<div>Hello Antares</div>")

    def test_slot_supports_directives(self):
        self._component("card", "<div>{{ slot }}</div>")

        template = "<pb-card>@for(item in items){{ item }}@endfor</pb-card>"

        self.assertEqual(self._render(template, {"items": ["a", "b"]}), "<div>ab</div>")

    def test_slot_markup_is_not_escaped(self):
        self._component("card", "<div>{{ slot }}</div>")

        result = self._render("<pb-card><em>{{ name }}</em></pb-card>", {"name": "<Antares>"})

        self.assertEqual(result, "<div><em>&lt;Antares&gt;</em></div>")

    def test_missing_slot_falls_back_to_the_component_default(self):
        self._component("card", '<div>{{ slot or "Empty" }}</div>')

        self.assertEqual(self._render("<pb-card />"), "<div>Empty</div>")


class TestNesting(ComponentTestCase):
    def test_nested_components(self):
        self._component("card", '<div class="card">{{ slot }}</div>')
        self._component("button", "<button>{{ label }}</button>")

        result = self._render('<pb-card><pb-button label="Go" /></pb-card>')

        self.assertEqual(result, '<div class="card"><button>Go</button></div>')

    def test_component_nested_in_a_component_of_the_same_name(self):
        self._component("card", '<div class="card">{{ slot }}</div>')

        result = self._render("<pb-card><pb-card>Inner</pb-card></pb-card>")

        self.assertEqual(result, '<div class="card"><div class="card">Inner</div></div>')

    def test_nested_slots(self):
        self._component("layout", "<div><h1>{{ title }}</h1><main>{{ slot }}</main></div>")
        self._component("card", '<div class="card"><h2>{{ heading }}</h2>{{ slot }}</div>')

        template = (
            "<pb-layout>"
            "<pb-slot:title>Dashboard</pb-slot:title>"
            "<pb-card><pb-slot:heading>Stats</pb-slot:heading>Body</pb-card>"
            "</pb-layout>"
        )

        self.assertEqual(
            self._render(template),
            '<div><h1>Dashboard</h1><main><div class="card"><h2>Stats</h2>Body</div></main></div>',
        )

    def test_slot_of_a_nested_component_resolves_outer_variables(self):
        self._component("card", "<div>{{ slot }}</div>")

        result = self._render("<pb-card><pb-card>{{ name }}</pb-card></pb-card>", {"name": "Antares"})

        self.assertEqual(result, "<div><div>Antares</div></div>")


class TestInheritanceSlots(ComponentTestCase):
    """Inheritance relies on the very same slot mechanism."""

    def test_inheritance_uses_the_same_slot_mechanism(self):
        self._write(
            "layouts.base",
            "<html><h1>{{ title }}</h1>@block('content')nothing@endblock<main>{{ slot }}</main></html>",
        )

        child = (
            "@extends('layouts.base')\n"
            "@slot('title')My page title@endslot\n"
            "@block('content')Page content@endblock\n"
            "Extra content here"
        )

        self.assertEqual(
            self._render(child),
            "<html><h1>My page title</h1>Page content<main>Extra content here</main></html>",
        )

    def test_components_can_be_used_in_inheritance_slots(self):
        self._component("card", '<div class="card">{{ slot }}</div>')
        self._write("layouts.base", "<html><h1>{{ title }}</h1><main>{{ slot }}</main></html>")

        child = (
            "@extends('layouts.base')"
            "<pb-slot:title>Dashboard</pb-slot:title>"
            "<pb-card>{{ name }}</pb-card>"
        )

        result = self._render(child, {"name": "Antares"})

        self.assertEqual(result, '<html><h1>Dashboard</h1><main><div class="card">Antares</div></main></html>')


if __name__ == "__main__":
    unittest.main()