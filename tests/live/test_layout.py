"""A live component rendered as a page of its own, inside the layout it names.

    path("app/", Home.as_view())

The component is not a whole document: it is the content of one. What surrounds
it is a layout, named by the component rather than written into its template,
and filled in the way any template fills the one it extends -- its markup
becoming the `slot` of the layout, and the slots it declares becoming the named
slots the layout reads.
"""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError
from pyblade.live.base import LiveComponent
from pyblade.live.decorators import layout


def without_snapshot(markup):
    """The markup with the snapshot the root element carries taken out."""
    return re.sub(r" pb:(?:snapshot|events)='[^']*'", "", markup)


class LayoutTestCase(unittest.TestCase):
    """A project with a templates directory and a components directory."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.templates_dir = self.root / "templates"
        self.components_dir = self.root / "components"
        self.templates_dir.mkdir()
        self.components_dir.mkdir()

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.templates_dir])

        self._saved_settings = {key: settings._data.get(key) for key in ("templates_dir", "components_dir")}
        settings._data["templates_dir"] = str(self.templates_dir)
        settings._data["components_dir"] = str(self.components_dir)

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        for key, value in self._saved_settings.items():
            if value is None:
                settings._data.pop(key, None)
            else:
                settings._data[key] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, name, content, directory=None):
        """Write a template file, `name` using dot notation (e.g. 'layouts.app')."""
        path = (directory or self.templates_dir) / f"{name.replace('.', '/')}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _layout(self, name="layouts.app", content=None):
        return self._write(name, content or "<body><main>{{ slot }}</main></body>")

    def _page(self, template_string, **body):
        """A component whose template is the given string, rendered as a page."""
        component = type(
            "Page",
            (LiveComponent,),
            {
                "render": lambda self: self.render_inline(template_string, context={}),
                **body,
            },
        )
        return component

    def _render(self, component, **properties):
        return component.render_initial({"key": "pb-test", **properties}, layout=component.get_layout_name())


class TestLayoutRendering(LayoutTestCase):
    """The markup of the component becomes the slot of its layout."""

    def test_component_markup_fills_the_slot_of_the_layout(self):
        self._layout()
        page = self._page("<div>Hello</div>")

        self.assertIn(
            '<main><div pb:id="pb-test">Hello</div></main>',
            without_snapshot(self._render(page)),
        )

    def test_slot_is_not_escaped(self):
        self._layout(content="<body>{{ slot }}</body>")
        page = self._page('<div class="a &amp; b">Hi</div>')

        rendered = self._render(page)

        self.assertNotIn("&lt;div", rendered)

    def test_the_whole_layout_is_rendered_around_the_component(self):
        self._layout(content="<html><head><title>App</title></head><body>{{ slot }}</body></html>")
        page = self._page("<div>Hello</div>")

        rendered = self._render(page)

        self.assertTrue(rendered.startswith("<html><head><title>App</title></head>"))
        self.assertIn("Hello", rendered)

    def test_state_of_the_component_is_rendered_in_its_own_template(self):
        self._layout()
        page = self._page("<div>{{ count }}</div>", count=3)

        self.assertIn('<div pb:id="pb-test">3</div>', without_snapshot(self._render(page)))

    def test_snapshot_rides_on_the_root_element_of_the_component(self):
        self._layout(content="<html><body><main>{{ slot }}</main></body></html>")
        page = self._page("<div>Hi</div>")

        rendered = self._render(page)

        self.assertIn("""<div pb:id="pb-test" pb:snapshot='{""", rendered)
        self.assertLess(rendered.index("pb:snapshot"), rendered.index("</body>"))


class TestNamedSlots(LayoutTestCase):
    """The slots a page component declares are read by its layout."""

    def test_named_slot_is_available_as_a_variable_in_the_layout(self):
        self._layout(content="<body><title>{{ title }}</title><main>{{ slot }}</main></body>")
        page = self._page('<div><pb-slot name="title">Home</pb-slot><h1>Hi</h1></div>')

        self.assertIn("<title>Home</title>", self._render(page))

    def test_named_slot_is_not_part_of_the_markup_of_the_component(self):
        self._layout(content="<body><main>{{ slot }}</main></body>")
        page = self._page('<div><pb-slot name="title">Home</pb-slot><h1>Hi</h1></div>')

        rendered = self._render(page)

        self.assertIn("<h1>Hi</h1>", rendered)
        self.assertNotIn("Home", rendered)

    def test_directive_syntax_declares_a_slot_too(self):
        self._layout(content="<body><title>{{ title }}</title>{{ slot }}</body>")
        page = self._page("<div>@slot('title')Home@endslot<h1>Hi</h1></div>")

        self.assertIn("<title>Home</title>", self._render(page))

    def test_layout_falls_back_to_its_own_content_for_a_slot_the_page_leaves_out(self):
        """As anywhere else, a name the layout reads has to be one it is given."""
        self._layout(content="<body><title>{{ title or 'Default' }}</title>{{ slot }}</body>")
        page = self._page("<div>Hi</div>", title=None)

        self.assertIn("<title>Default</title>", self._render(page))

    def test_slot_declared_before_the_root_element_leaves_the_root_element_alone(self):
        """The id of the component belongs on its markup, never on a slot it declares."""
        self._layout(content="<body><title>{{ title }}</title>{{ slot }}</body>")
        page = self._page('<pb-slot name="title">Home</pb-slot><div>Hi</div>')

        rendered = self._render(page)

        self.assertIn("<title>Home</title>", rendered)
        self.assertIn('<div pb:id="pb-test">Hi</div>', without_snapshot(rendered))


class TestLayoutResolution(LayoutTestCase):
    """Which layout a component renders inside."""

    def test_default_layout(self):
        self._layout("layouts.app", "<body>default layout {{ slot }}</body>")
        page = self._page("<div>Hi</div>")

        self.assertIn("default layout", self._render(page))

    def test_layout_decorator(self):
        self._layout("layouts.app", "<body>default layout {{ slot }}</body>")
        self._layout("layouts.admin", "<body>admin layout {{ slot }}</body>")
        page = layout("layouts.admin")(self._page("<div>Hi</div>"))

        self.assertIn("admin layout", self._render(page))

    def test_layout_name_attribute(self):
        self._layout("layouts.app", "<body>default layout {{ slot }}</body>")
        self._layout("layouts.admin", "<body>admin layout {{ slot }}</body>")
        page = self._page("<div>Hi</div>", layout_name="layouts.admin")

        self.assertIn("admin layout", self._render(page))

    def test_layout_name_is_not_part_of_the_state_sent_to_the_client(self):
        self._layout()
        page = self._page("<div>Hi</div>", layout_name="layouts.app")

        self.assertNotIn("layout_name", page("pb-test")._get_state())

    def test_a_template_that_extends_a_layout_of_its_own_keeps_it(self):
        self._layout("layouts.app", "<body>default layout {{ slot }}</body>")
        self._layout("layouts.admin", "<body>admin layout {{ slot }}</body>")
        page = self._page("@extends('layouts.admin')<div>Hi</div>")

        self.assertIn("admin layout", self._render(page))

    def test_missing_default_layout_leaves_the_component_on_its_own(self):
        """A project with no layouts/app.html still renders the pages it declares."""
        page = self._page("<div>Hi</div>")

        self.assertIn('<div pb:id="pb-test">Hi</div>', without_snapshot(self._render(page)))

    def test_missing_declared_layout_is_reported(self):
        page = self._page("<div>Hi</div>", layout_name="layouts.nowhere")

        with self.assertRaises(TemplateNotFoundError):
            self._render(page)


class TestComponentsThatAreNotPages(LayoutTestCase):
    """Only a component rendered as a page of its own is wrapped in a layout."""

    def test_component_rendered_inside_a_page_gets_no_layout(self):
        self._layout()
        page = self._page("<div>Hi</div>")

        rendered = without_snapshot(page.render_initial({"key": "pb-test"}))

        self.assertNotIn("<main>", rendered)
        self.assertTrue(rendered.startswith('<div pb:id="pb-test">'))

    def test_action_answers_with_the_component_alone(self):
        """What is morphed back into the page is the component, not the page."""
        self._layout()
        page = self._page(
            "<div>{{ count }}</div>",
            count=0,
            increment=lambda self: setattr(self, "count", 1),
        )

        response = page.update_component({"_id": "pb-test", "count": 0}, "increment")

        self.assertEqual(response["html"], '<div pb:id="pb-test">1</div>')

    def test_action_answers_without_the_slots_the_layout_reads(self):
        self._layout(content="<body><title>{{ title }}</title>{{ slot }}</body>")
        page = self._page('<div><pb-slot name="title">Home</pb-slot><h1>Hi</h1></div>')

        response = page.update_component({"_id": "pb-test"}, "$refresh")

        self.assertNotIn("Home", response["html"])
        self.assertIn("<h1>Hi</h1>", response["html"])


class TestAsView(LayoutTestCase):
    """The Django view a page component is turned into."""

    def _request(self):
        from django.test import RequestFactory

        return RequestFactory().get("/app/")

    def test_view_answers_with_the_page(self):
        self._layout(content="<html><body><main>{{ slot }}</main></body></html>")
        page = self._page("<div>Hi</div>")

        response = page.as_view()(self._request())
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn('<main><div pb:id="', content)
        self.assertIn("Hi", content)
        self.assertTrue(content.startswith("<html>"))

    def test_view_carries_the_arguments_of_the_route_to_mount(self):
        self._layout()
        page = self._page(
            "<div>{{ count }}</div>",
            mount=lambda self, start=0: setattr(self, "count", start),
        )

        content = page.as_view()(self._request(), start=7).content.decode()

        self.assertIn(">7<", content)

    def test_a_page_that_goes_wrong_is_shown_while_developing(self):
        """The same page the engine shows for any other template that went wrong."""
        from django.test import override_settings

        self._layout()
        page = self._page("<div>{{ nowhere }}</div>")

        with override_settings(DEBUG=True):
            response = page.as_view()(self._request())

        content = response.content.decode()

        self.assertEqual(response.status_code, 500)
        self.assertIn("Undefined variable", content)
        self.assertIn("development mode", content.lower())

    def test_what_went_wrong_is_not_shown_in_production(self):
        """An error's message never reaches the browser once it is not development."""
        from django.test import override_settings

        self._layout()
        page = self._page("<div>{{ nowhere }}</div>")

        with override_settings(DEBUG=False), self.assertRaises(Exception) as raised:
            page.as_view()(self._request())

        self.assertIn("nowhere", str(raised.exception))

    def test_view_names_the_component_it_renders(self):
        page = self._page("<div>Hi</div>")

        self.assertIs(page.as_view().component, page)


class TestALazyPage(LayoutTestCase):
    """A page that keeps nobody waiting is still a page.

    A lazy component skips its own rendering, and the layout is what carries the
    scripts that would ask for it: skipping that too would leave a skeleton on a
    page with no PyBlade on it, waiting for something that never comes.
    """

    def _lazy_page(self, **body):
        from pyblade.live.decorators import lazy

        return lazy(self._page("<div>Loaded</div>", **body))

    def test_the_layout_is_rendered_around_the_skeleton(self):
        self._layout(content="<html><head><title>App</title></head><body>{{ slot }}</body></html>")

        rendered = self._render(self._lazy_page())

        self.assertTrue(rendered.startswith("<html><head><title>App</title></head>"))
        self.assertIn("pb-skeleton", rendered)

    def test_the_skeleton_is_the_component_of_the_page(self):
        self._layout()

        rendered = self._render(self._lazy_page())

        self.assertIn('pb:id="pb-test"', rendered)
        self.assertIn("pb:snapshot=", rendered)

    def test_the_id_is_written_once(self):
        self._layout()

        self.assertEqual(self._render(self._lazy_page()).count('pb:id="pb-test"'), 1)

    def test_a_placeholder_of_its_own_is_given_the_layout_too(self):
        self._layout(content="<html><body>{{ slot }}</body></html>")
        page = self._lazy_page(
            placeholder=lambda self: self.render_inline("<div>Just a moment</div>", context={}),
        )

        rendered = self._render(page)

        self.assertTrue(rendered.startswith("<html><body>"))
        self.assertIn("Just a moment", rendered)


class TestRenderingAnotherTemplate(LayoutTestCase):
    """A component may render a template other than its own.

    Its own is what it renders when it says nothing, which is what a component
    does. Naming one is for the times a component has more than one way to look:
    the skeleton a lazy component shows before it has loaded, above all.
    """

    def _component(self, **body):
        return type("Page", (LiveComponent,), body)

    def test_the_template_named_is_the_one_rendered(self):
        self._layout()
        self._write("skeletons.figures", "<div>Still counting</div>")
        page = self._component(render=lambda self: self.render_template("skeletons.figures"))

        self.assertIn("Still counting", self._render(page))

    def test_it_is_rendered_as_the_component(self):
        """The id lands on its root, and what the component holds is in it."""
        self._layout()
        self._write("skeletons.figures", "<div>{{ count }} so far</div>")
        page = self._component(count=7, render=lambda self: self.render_template("skeletons.figures"))

        rendered = without_snapshot(self._render(page))

        self.assertIn('<div pb:id="pb-test">7 so far</div>', rendered)

    def test_the_layout_is_rendered_around_it(self):
        self._layout(content="<html><body>{{ slot }}</body></html>")
        self._write("skeletons.figures", "<div>Still counting</div>")
        page = self._component(render=lambda self: self.render_template("skeletons.figures"))

        self.assertTrue(self._render(page).startswith("<html><body>"))

    def test_a_template_that_is_not_there_is_said_so_by_name(self):
        self._layout()
        page = self._component(render=lambda self: self.render_template("skeletons.nowhere"))

        with self.assertRaises(TemplateNotFoundError) as caught:
            self._render(page)

        self.assertIn("skeletons.nowhere", str(caught.exception))

    def test_naming_nothing_still_renders_the_component_s_own(self):
        self._layout()
        self._write("figures", "<div>The component's own</div>", directory=self.components_dir)
        page = self._component(template_name="figures", render=lambda self: self.render_template())

        self.assertIn("The component's own", self._render(page))

    def test_a_context_may_still_be_given_as_it_always_could(self):
        self._layout()
        self._write("skeletons.figures", "<div>{{ note }}</div>")
        page = self._component(render=lambda self: self.render_template("skeletons.figures", {"note": "Hold on"}))

        self.assertIn("Hold on", self._render(page))
