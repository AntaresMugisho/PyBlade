"""What the page is told when a live component goes wrong.

While developing, an error nobody caught comes back as the PyBlade error page,
so the browser can show it over the page the developer is working on rather than
leaving them with a page that has quietly stopped working. In production it is
left alone: what that page holds -- paths, code, frames -- is for whoever is
writing the code and for nobody else.
"""

import json
import sys
import unittest

from django.test import RequestFactory, override_settings

from pyblade.live.base import LiveComponent
from pyblade.live.registry import registry
from pyblade.live.security import generate_checksum
from pyblade.live.views import update_component


class Fragile(LiveComponent):
    title = ""

    def explode(self):
        raise ValueError("A post needs a title")

    def crash(self):
        raise TypeError("nothing to be done about this one")

    def render(self):
        return self.render_inline("<div>{{ title }}</div>", context={})


class Broken(LiveComponent):
    """A component whose template cannot be rendered."""

    title = ""

    def render(self):
        return self.render_inline("<div>@for(a, b in title)x@endfor</div>", context={})


class ErrorTestCase(unittest.TestCase):
    component_class = Fragile
    debug = True

    def setUp(self):
        self.override = override_settings(DEBUG=self.debug)
        self.override.enable()

        self.path = f"{__name__}.{self.component_class.__name__}"
        registry.register(self.path, self.component_class)
        self.requests = RequestFactory()

    def tearDown(self):
        self.override.disable()
        registry._components.pop(self.path, None)

    def _post(self, action="explode"):
        instance = self.component_class("pb-test")
        snapshot = instance.serialize()
        snapshot["class"] = self.path
        snapshot.pop("checksum")
        snapshot["checksum"] = generate_checksum(snapshot)

        request = self.requests.post(
            "/pyblade/live/",
            data=json.dumps({"snapshot": snapshot, "action": action, "params": []}),
            content_type="application/json",
        )

        return update_component(request)

    def _body(self, response):
        return json.loads(response.content)


class TestWhileDeveloping(ErrorTestCase):
    def test_an_error_nobody_caught_is_answered_rather_than_raised(self):
        self.assertEqual(self._post().status_code, 500)

    def test_what_went_wrong_comes_back(self):
        body = self._body(self._post())

        self.assertIn("A post needs a title", body["error"])

    def test_the_page_comes_back_with_it(self):
        body = self._body(self._post())

        self.assertIn("<!DOCTYPE html>", body["page"])
        self.assertIn("ValueError", body["page"])
        self.assertIn("A post needs a title", body["page"])

    def test_the_page_says_where_it_came_through(self):
        self.assertIn("explode", self._body(self._post())["page"])


class TestATemplateThatCannotBeRendered(ErrorTestCase):
    component_class = Broken

    def test_the_page_names_the_error(self):
        body = self._body(self._post(action="$refresh"))

        self.assertEqual(self._body(self._post(action="$refresh")).keys(), body.keys())
        self.assertIn("DirectiveParsingError", body["page"])

    def test_and_shows_the_template_it_happened_in(self):
        body = self._body(self._post(action="$refresh"))

        self.assertIn("@for", body["page"])


class TestInProduction(ErrorTestCase):
    debug = False

    def test_an_error_nobody_caught_is_left_to_the_framework(self):
        with self.assertRaises(TypeError):
            self._post(action="crash")

    def test_a_value_error_of_the_component_is_left_to_the_framework_too(self):
        """Not answered 404 with its message: what went wrong is for the logs."""
        with self.assertRaises(ValueError):
            self._post()

    def test_a_component_that_cannot_be_found_is_not_found(self):
        from pyblade.live.registry import ComponentNotFound

        def missing(self):
            raise ComponentNotFound("PyBlade Live Component 'secret.path.Thing' could not be resolved.")

        self.component_class.explode_missing = missing
        try:
            response = self._post(action="explode_missing")
        finally:
            del self.component_class.explode_missing

        self.assertEqual(response.status_code, 404)
        self.assertNotIn("secret.path", response.content.decode())


class TestAnActionThatAnswersAsItGoes(unittest.TestCase):
    """A stream cannot answer 500 half way through: it says so in a line."""

    debug = True

    def setUp(self):
        self.override = override_settings(DEBUG=self.debug)
        self.override.enable()

        from pyblade.live.decorators import streamed

        class Streamer(LiveComponent):
            word = ""

            @streamed
            def tell(self):
                self.stream("out", "half a ")
                raise ValueError("and then nothing")

            def render(self):
                return self.render_inline("<div>{{ word }}</div>", context={})

        self.component_class = Streamer
        self.path = f"{__name__}.Streamer"
        sys.modules[__name__].Streamer = Streamer
        registry.register(self.path, Streamer)
        self.requests = RequestFactory()

    def tearDown(self):
        self.override.disable()
        registry._components.pop(self.path, None)

    def _lines(self):
        instance = self.component_class("pb-test")
        snapshot = instance.serialize()
        snapshot["class"] = self.path
        snapshot.pop("checksum")
        snapshot["checksum"] = generate_checksum(snapshot)

        request = self.requests.post(
            "/pyblade/live/",
            data=json.dumps({"snapshot": snapshot, "action": "tell", "params": []}),
            content_type="application/json",
        )

        response = update_component(request)

        return [json.loads(line) for line in b"".join(response.streaming_content).splitlines() if line]

    def test_what_it_streamed_before_it_went_wrong_still_arrives(self):
        self.assertEqual(self._lines()[0]["stream"]["content"], "half a ")

    def test_the_last_line_says_what_went_wrong_and_carries_the_page(self):
        last = self._lines()[-1]

        self.assertIn("and then nothing", last["error"])
        self.assertIn("<!DOCTYPE html>", last["page"])

    def test_in_production_it_says_what_went_wrong_and_no_more(self):
        with override_settings(DEBUG=False):
            last = self._lines()[-1]

        self.assertIn("error", last)
        self.assertNotIn("page", last)


# The endpoint resolves a component by the path it is registered under, which is
# this module's own name
sys.modules[__name__].Fragile = Fragile
sys.modules[__name__].Broken = Broken
