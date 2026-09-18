"""@persist: markup the page keeps as it is, through updates and navigation.

The server's part is only to mark it; keeping it is the client's.
"""

import unittest

from pyblade.engine.exceptions import DirectiveParsingError, TemplateRenderError
from pyblade.engine.processor import TemplateProcessor


class TestPersist(unittest.TestCase):
    def _render(self, template, context=None):
        return TemplateProcessor().render(template, context or {})

    def test_the_content_is_wrapped_in_an_element_carrying_its_name(self):
        html = self._render("@persist('player')<video src=\"/live\"></video>@endpersist")

        self.assertEqual(html, '<div data-pb-persist="player"><video src="/live"></video></div>')

    def test_the_content_renders_with_the_context_it_is_written_in(self):
        html = self._render("@persist('player')<p>{{ title }}</p>@endpersist", {"title": "Live"})

        self.assertEqual(html, '<div data-pb-persist="player"><p>Live</p></div>')

    def test_the_name_may_be_an_expression(self):
        html = self._render("@persist(name)x@endpersist", {"name": "chat"})

        self.assertEqual(html, '<div data-pb-persist="chat">x</div>')

    def test_the_name_is_escaped(self):
        html = self._render("@persist(name)x@endpersist", {"name": '"><script>'})

        self.assertNotIn("<script>", html)

    def test_a_name_is_required(self):
        with self.assertRaises((DirectiveParsingError, TemplateRenderError)):
            self._render("@persist x@endpersist")

    def test_an_unclosed_persist_is_an_error(self):
        with self.assertRaises(TemplateRenderError):
            self._render("@persist('player')<video></video>")


if __name__ == "__main__":
    unittest.main()
