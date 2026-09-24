"""The page PyBlade shows a developer when something has gone wrong.

It is built in one place, from any exception: one raised while a template was
being rendered, which knows the file and the line it happened on, and an
ordinary Python one raised by an action, which knows neither and brings a
traceback instead.
"""

import unittest
from pathlib import Path

from pyblade.engine.exceptions import TemplateRenderError
from pyblade.engine.renderer import error_page


class TestWhatThePageSays(unittest.TestCase):
    def test_it_names_what_went_wrong(self):
        page = error_page(ValueError("A post needs a title"))

        self.assertIn("ValueError", page)
        self.assertIn("A post needs a title", page)

    def test_it_is_a_page_of_its_own(self):
        self.assertIn("<!DOCTYPE html>", error_page(ValueError("nope")))

    def test_it_says_it_is_only_shown_while_developing(self):
        self.assertIn("development mode", error_page(ValueError("nope")).lower())


class TestAnErrorFromATemplate(unittest.TestCase):
    """One raised while rendering knows where it happened."""

    def setUp(self):
        self.source = "\n".join(f"line {number}" for number in range(1, 11))
        self.error = TemplateRenderError("Something is wrong here", line=5)

    def test_the_file_it_happened_in_is_shown(self):
        page = error_page(self.error, self.source, Path("components/post/post.html"))

        self.assertIn("components/post/post.html", page)

    def test_the_lines_around_it_are_shown(self):
        page = error_page(self.error, self.source, Path("post.html"))

        self.assertIn("line 5", page)
        self.assertIn("line 4", page)

    def test_the_line_it_happened_on_is_marked(self):
        page = error_page(self.error, self.source, Path("post.html"))

        marked = page.split('id="code-lines"')[1]

        self.assertIn("line-highlight", marked)


class TestAnErrorFromAnAction(unittest.TestCase):
    """One raised by a component's own code knows no template at all."""

    def _raised(self):
        def inner():
            raise ValueError("A post needs a title")

        try:
            inner()
        except ValueError as error:
            return error

    def test_the_traceback_is_shown_instead_of_a_template(self):
        page = error_page(self._raised())

        self.assertIn("Traceback", page)
        self.assertIn("inner", page)

    def test_nothing_is_said_about_a_template_there_is_none_of(self):
        page = error_page(self._raised())

        self.assertNotIn("Template file:", page)
        self.assertNotIn('id="code-lines"', page)

    def test_what_it_holds_is_written_as_text_rather_than_as_markup(self):
        """A message holding a tag must not become one."""
        page = error_page(ValueError("<script>alert('x')</script>"))

        self.assertNotIn("<script>alert", page)


class TestWhenItIsShown(unittest.TestCase):
    """The page is for whoever is writing the code, and only for them.

    Which means the question "are we developing?" has to be answered correctly,
    including for a project that never said which framework it is built on.
    """

    def setUp(self):
        from pyblade.config import settings

        self.settings = settings
        self.saved = settings._data.get("framework")

    def tearDown(self):
        if self.saved is None:
            self.settings._data.pop("framework", None)
        else:
            self.settings._data["framework"] = self.saved

    def test_a_project_that_says_it_is_django(self):
        from django.test import override_settings

        self.settings._data["framework"] = "django"

        with override_settings(DEBUG=True):
            self.assertIs(self.settings.DEBUG, True)

        with override_settings(DEBUG=False):
            self.assertIs(self.settings.DEBUG, False)

    def test_a_project_that_never_said_which_framework_it_is(self):
        """Django is answering, and is in development: so are we."""
        from django.test import override_settings

        self.settings._data.pop("framework", None)

        with override_settings(DEBUG=True):
            self.assertIs(self.settings.DEBUG, True)

    def test_and_is_not_in_development_when_that_framework_is_not(self):
        from django.test import override_settings

        self.settings._data.pop("framework", None)

        with override_settings(DEBUG=False):
            self.assertIs(self.settings.DEBUG, False)
