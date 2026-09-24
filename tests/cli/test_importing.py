"""Importing PyBlade must not need a web framework.

`pyblade init` exists to start a project with a framework that is not installed
yet, and the CLI imports PyBlade before it can do anything at all. So whatever
needs Django has to be reached only when somebody reaches for it -- otherwise
the one command that matters most to a new user is the one that cannot run.

Django is installed for this suite, so the question is asked of a fresh
interpreter with Django hidden from it.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

#: Hides a package from the import system, however it is asked for.
_BLOCK = """
import sys


class Blocked:
    def find_module(self, name, path=None):
        return self if name == "django" or name.startswith("django.") else None

    def find_spec(self, name, path=None, target=None):
        if name == "django" or name.startswith("django."):
            raise ModuleNotFoundError("No module named 'django'")
        return None


sys.meta_path.insert(0, Blocked())
for name in [name for name in sys.modules if name.startswith("django")]:
    del sys.modules[name]
"""


def _run(script):
    result = subprocess.run(
        [sys.executable, "-c", _BLOCK + script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parent.parent.parent,
    )

    return result


class TestWithNoFrameworkInstalled(unittest.TestCase):
    def test_pyblade_itself_imports(self):
        result = _run("import pyblade; print('ok')")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_so_does_everything_the_cli_needs(self):
        result = _run("""
import json
from pyblade.cli.main import cli
from pyblade.config import config

print(json.dumps({"locale": config.i18n.locale, "debug": config.DEBUG}))
""")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"locale": "en", "debug": False})

    def test_and_the_engine_renders(self):
        """The template engine is PyBlade's own; none of it is Django's."""
        result = _run("""
from pyblade.engine.processor import TemplateProcessor

print(TemplateProcessor().render("@if(True)hello {{ name }}@endif", {"name": "world"}))
""")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hello world", result.stdout)

    def test_a_live_component_is_what_says_it_needs_one(self):
        """Reaching for it is what raises, and it says what is missing."""
        result = _run("""
import pyblade

try:
    pyblade.LiveComponent
except ModuleNotFoundError as error:
    print(error)
""")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("django", result.stdout)
