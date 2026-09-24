import shutil
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

from pyblade.config import config
from pyblade.engine import loader
from pyblade.engine.exceptions import TemplateNotFoundError


class TestDefaultLoader(unittest.TestCase):
    """Where a template is looked for when nobody said."""

    def setUp(self):
        self.project_dir = Path(tempfile.mkdtemp())
        (self.project_dir / "templates" / "layouts").mkdir(parents=True)
        (self.project_dir / "templates" / "layouts" / "app.html").write_text("<html>{{ slot }}</html>")

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader._template_dirs = []

        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(config.override({"paths.templates": str(self.project_dir / "templates")}))

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def test_the_templates_directory_of_the_project_is_searched(self):
        """A page rendered before any backend was built still finds its layout."""
        template = loader.load_template("layouts.app")

        self.assertEqual(template.content, "<html>{{ slot }}</html>")

    def test_a_template_that_is_nowhere_is_still_reported(self):
        with self.assertRaises(TemplateNotFoundError):
            loader.load_template("layouts.nowhere")

    def test_a_configured_directory_comes_first(self):
        other = self.project_dir / "other"
        (other / "layouts").mkdir(parents=True)
        (other / "layouts" / "app.html").write_text("<html>from the configured one</html>")
        loader._default_loader.add_directories([other])

        self.assertEqual(
            loader.load_template("layouts.app").content,
            "<html>from the configured one</html>",
        )


class TestTheDjangoBackend(unittest.TestCase):
    """What Django is told when a template it asked for is not there.

    Django asks each engine in turn for a template, and an engine that has not
    got it says so by raising TemplateDoesNotExist. An engine that raises
    anything else stops the search: a template held by another engine would
    never be reached, and Django's own page saying where it looked is never
    shown.
    """

    def _backend(self):
        from pyblade.backends.django import PyBladeEngine

        return PyBladeEngine({"NAME": "pyblade", "DIRS": [], "APP_DIRS": False, "OPTIONS": {}})

    def test_a_template_that_is_not_there_is_said_the_way_django_says_it(self):
        from django.template import TemplateDoesNotExist

        with self.assertRaises(TemplateDoesNotExist):
            self._backend().get_template("no_such_template_anywhere")

    def test_and_is_still_what_pyblade_calls_it(self):
        """So that code catching PyBlade's own exception goes on working."""
        with self.assertRaises(TemplateNotFoundError):
            self._backend().get_template("no_such_template_anywhere")
