"""Binding PyBlade to a web framework.

Every binding does the same three things: get an engine, render a template by
name with the request in its context, and hand back whatever that framework
calls an HTML response. Only the last differs, so only the last is written out
per framework -- and none of it may be imported until somebody asks for it,
because importing PyBlade must not need a framework installed.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pyblade.backends import base
from pyblade.config import config


class BackendTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        self.templates = self.root / "templates"
        self.templates.mkdir()

        base.reset()
        self.addCleanup(base.reset)

    def write(self, name, content):
        (self.templates / f"{name}.html").write_text(content)


class TestWhereTemplatesAreLookedFor(BackendTestCase):
    def test_what_the_framework_says_is_used(self):
        self.assertEqual(base.directories("here", "there"), ["here", "there"])

    def test_and_the_project_answers_when_it_says_nothing(self):
        with config.override({"paths.templates": "pages"}):
            self.assertEqual(base.directories(), [str(config.root / "pages")])

    def test_a_framework_that_names_nothing_is_not_counted(self):
        with config.override({"paths.templates": "pages"}):
            self.assertEqual(base.directories(None, ""), [str(config.root / "pages")])


class TestRenderingATemplate(BackendTestCase):
    def test_a_template_is_loaded_by_name_and_rendered(self):
        """Not rendered *as* the name, which is what render() would do with one."""
        self.write("home", "<h1>{{ title }}</h1>")

        html = base.render(base.configure(self.templates), "home", {"title": "Shop"})

        self.assertEqual(html.strip(), "<h1>Shop</h1>")

    def test_the_directives_in_it_run(self):
        self.write("home", "@if(loud)<b>{{ word }}</b>@else{{ word }}@endif")

        engine = base.configure(self.templates)

        self.assertEqual(base.render(engine, "home", {"loud": True, "word": "hi"}).strip(), "<b>hi</b>")

    def test_the_request_is_put_in_the_context_when_there_is_one(self):
        self.write("home", "{{ request }}")

        html = base.render(base.configure(self.templates), "home", {}, request="A REQUEST")

        self.assertEqual(html.strip(), "A REQUEST")

    def test_and_the_context_it_was_given_is_left_alone(self):
        self.write("home", "{{ request }}")
        context = {}

        base.render(base.configure(self.templates), "home", context, request="A REQUEST")

        self.assertEqual(context, {})


class TestOneEnginePerApplication(BackendTestCase):
    """Flask and Quart can run several applications in one process."""

    class App:
        """Something that can be weakly referenced, as an application can."""

    def test_the_same_application_gets_the_same_engine(self):
        app = self.App()

        self.assertIs(base.engine_for(app, self.templates), base.engine_for(app, self.templates))

    def test_and_another_application_gets_its_own(self):
        self.assertIsNot(base.engine_for(self.App(), self.templates), base.engine_for(self.App(), self.templates))

    def test_an_application_that_goes_away_takes_its_engine_with_it(self):
        app = self.App()
        base.engine_for(app, self.templates)
        self.assertEqual(len(base._per_app), 1)

        del app

        self.assertEqual(len(base._per_app), 0)

    def test_something_that_cannot_be_weakly_referenced_shares_the_one_engine(self):
        base.configure(self.templates)

        self.assertIs(base.engine_for(object(), self.templates), base.shared_engine())


class TestImportingWithoutTheFramework(unittest.TestCase):
    """A framework module is the point at which its framework has to be there."""

    def _run(self, script):
        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parent.parent.parent,
        )

    def test_the_shared_part_needs_nothing(self):
        result = self._run("from pyblade.backends import base; print('ok')")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_the_django_backend_is_not_imported_until_it_is_asked_for(self):
        """Every generated settings.py names it, so asking must still work.

        PyBlade imports Django's CSRF helpers when Django happens to be there,
        which is why this asks about PyBlade's own Django module rather than
        about Django itself.
        """
        result = self._run("""
import sys

import pyblade.backends

print("backend imported by the package:", "pyblade.backends.django" in sys.modules)
print("resolves:", pyblade.backends.PyBladeEngine.__name__)
print("backend imported once asked:", "pyblade.backends.django" in sys.modules)
""")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("backend imported by the package: False", result.stdout)
        self.assertIn("resolves: PyBladeEngine", result.stdout)
        self.assertIn("backend imported once asked: True", result.stdout)

    def test_a_framework_module_says_what_is_missing(self):
        result = self._run("""
try:
    import pyblade.starlette
except ModuleNotFoundError as error:
    print("missing:", error.name)
""")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("missing: starlette", result.stdout)


class TestTheFlaskBinding(BackendTestCase):
    """Flask is a development dependency, so this one can be run for real."""

    def test_it_serves_a_rendered_template(self):
        from flask import Flask

        from pyblade.flask import render

        self.write("home", "@extends('layout')<p>{{ word }}</p>")
        self.write("layout", "<main>{{ slot }}</main>")

        app = Flask(__name__, template_folder=str(self.templates))

        @app.route("/")
        def home():
            return render("home", word="hello")

        with app.test_client() as client:
            answer = client.get("/")

        self.assertEqual(answer.status_code, 200)
        self.assertEqual(answer.get_data(as_text=True).strip(), "<main><p>hello</p></main>")
        self.assertTrue(answer.content_type.startswith("text/html"))

    def test_the_name_flask_users_know_is_there_too(self):
        from pyblade.flask import render, render_template

        self.assertIs(render_template, render)
