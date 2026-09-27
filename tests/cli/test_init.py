"""Where `pyblade init` puts a project, and what it calls it.

A project may be started in a directory of its own, or in the one you are
already standing in. The second is what '.' means, and it splits a question
that was one question before: a directory is free to be called 'my-shop', and
a Python package is not, so where the project goes and what it is called stop
being the same answer.
"""

import importlib
import os
import shutil
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

from pyblade.cli import packages

init = importlib.import_module("pyblade.cli.commands.init")

Project = namedtuple("Project", "name framework tailwind")


class InitTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        self.command = init.Command()

    def asked_for(self, name, inside=None):
        """Set the command up as though somebody had typed that name."""
        if inside:
            directory = self.root / inside
            directory.mkdir(parents=True, exist_ok=True)
            cwd = os.getcwd()
            os.chdir(directory)
            self.addCleanup(os.chdir, cwd)

        self.command.project = Project(name, "django", False)
        self.command.directory = Path.cwd() if name == init.Command.HERE else Path(name)

        return self.command


class TestAProjectInADirectoryOfItsOwn(InitTestCase):
    def test_the_name_given_is_the_package_name(self):
        command = self.asked_for("shop")

        self.assertEqual(command._package_name(), "shop")

    def test_and_the_directory_is_named_after_it(self):
        command = self.asked_for("shop")

        self.assertEqual(command.directory, Path("shop"))


class TestAProjectStartedWhereYouAreStanding(InitTestCase):
    def test_the_directory_is_the_one_you_are_in(self):
        command = self.asked_for(".", inside="shop")

        self.assertEqual(command.directory.resolve(), (self.root / "shop").resolve())

    def test_the_package_is_named_after_that_directory(self):
        command = self.asked_for(".", inside="shop")

        self.assertEqual(command._package_name(), "shop")

    def test_a_directory_name_a_package_may_not_have_is_tidied(self):
        """'my-shop' is a fine directory and not a Python name."""
        command = self.asked_for(".", inside="my-shop")

        self.assertEqual(command._package_name(), "my_shop")

    def test_a_name_that_cannot_be_tidied_is_not_guessed_at(self):
        command = self.asked_for(".", inside="123")

        self.assertIsNone(command._package_name())

    def test_nor_is_one_that_python_has_taken(self):
        command = self.asked_for(".", inside="class")

        self.assertIsNone(command._package_name())


class TestNotWritingOverSomebodysWork(InitTestCase):
    def test_a_directory_holding_a_project_is_refused(self):
        command = self.asked_for(".", inside="shop")
        (command.directory / "manage.py").touch()

        self.assertFalse(command._place_is_free())

    def test_so_is_one_that_pyblade_has_already_been_run_in(self):
        command = self.asked_for(".", inside="shop")
        (command.directory / "pyblade.toml").touch()

        self.assertFalse(command._place_is_free())

    def test_an_empty_directory_is_free(self):
        command = self.asked_for(".", inside="shop")

        self.assertTrue(command._place_is_free())

    def test_a_directory_with_other_things_in_it_is_free_too(self):
        """Somebody may have made the directory and put a README in it first."""
        command = self.asked_for(".", inside="shop")
        (command.directory / "README.md").write_text("mine")

        self.assertTrue(command._place_is_free())

    def test_a_named_project_that_already_exists_is_refused(self):
        command = self.asked_for(".", inside="workspace")
        (Path.cwd() / "shop").mkdir()
        command.project = Project("shop", "django", False)
        command.directory = Path("shop")

        self.assertFalse(command._place_is_free())


class TestSettingUpADirectoryThatIsNotEmpty(InitTestCase):
    """uv and Poetry both refuse to initialise over an existing pyproject.toml."""

    def test_a_dependency_file_that_is_already_there_is_noticed(self):
        (self.root / "pyproject.toml").write_text('[project]\nname = "x"\n')

        self.assertTrue(packages.environment_exists("uv", self.root))
        self.assertTrue(packages.environment_exists("poetry", self.root))

    def test_and_an_empty_directory_has_nothing(self):
        self.assertFalse(packages.environment_exists("uv", self.root))
        self.assertFalse(packages.environment_exists("pip", self.root))
        self.assertFalse(packages.environment_exists("pipenv", self.root))

    def test_what_to_type_next_has_nowhere_to_go_when_you_are_already_there(self):
        self.assertEqual(packages.activation_line("uv", "."), "source .venv/bin/activate")
        self.assertEqual(packages.activation_line("uv", "shop"), "cd shop && source .venv/bin/activate")


class TestTheFrameworksItCanStart(InitTestCase):
    def test_each_one_is_given_what_it_needs_to_run(self):
        requires = init.Command.REQUIRES

        self.assertEqual(requires["django"], ["django", "pyblade"])
        self.assertEqual(requires["flask"], ["flask", "pyblade"])

    def test_fastapi_is_given_a_server_too(self):
        """It ships none of its own, so a scaffolded project could not be run."""
        self.assertIn("uvicorn", init.Command.REQUIRES["fastapi"])

    def test_every_one_of_them_is_given_pyblade(self):
        """A project renders its own templates; PyBlade is not a global tool to it."""
        for framework, requires in init.Command.REQUIRES.items():
            self.assertIn("pyblade", requires, framework)


class TestScaffoldingAFrameworkThatScaffoldsNothing(InitTestCase):
    """Django brings django-admin. Flask and FastAPI bring no such thing."""

    def scaffold(self, framework, tailwind=False):
        command = self.command
        command.project = Project(framework, framework, tailwind)
        command.directory = self.root
        command.package = framework
        command.manager = "uv"

        self.assertTrue(command._write_application(self.root))

        return command

    def test_flask_gets_an_application_module(self):
        self.scaffold("flask")
        written = (self.root / "app.py").read_text()

        self.assertIn("from flask import Flask", written)
        self.assertIn("from pyblade.flask import render", written)
        self.assertIn('@app.route("/")', written)

    def test_fastapi_gets_one_under_the_name_it_uses(self):
        self.scaffold("fastapi")
        written = (self.root / "main.py").read_text()

        self.assertIn("from fastapi import FastAPI, Request", written)
        self.assertIn("from pyblade.fastapi import render", written)

    def test_the_module_is_named_after_the_project(self):
        self.scaffold("flask")

        self.assertIn("flask, a Flask application", (self.root / "app.py").read_text())

    def test_django_is_not_written_one(self):
        """django-admin lays it out, so there is nothing here to write."""
        self.assertNotIn("django", init.APPLICATION_FILE)


class TestTheTemplatesAProjectStartsWith(InitTestCase):
    def prepare(self, framework, tailwind):
        from pyblade.config import Config

        command = self.command
        command.project = Project("shop", framework, tailwind)
        command.directory = self.root
        command.package = "shop"
        command.settings = Config(config_file=self.root / "pyblade.toml")
        (self.root / "templates").mkdir(parents=True, exist_ok=True)

        command._write_templates()

        return self.root / "templates"

    def test_a_project_without_tailwind_still_gets_a_layout(self):
        templates = self.prepare("flask", tailwind=False)

        self.assertTrue((templates / "layout.html").exists())

    def test_one_with_tailwind_is_left_for_tailwind_to_lay_out(self):
        templates = self.prepare("flask", tailwind=True)

        self.assertFalse((templates / "layout.html").exists())

    def test_a_framework_pyblade_routes_itself_gets_a_page_to_see(self):
        templates = self.prepare("flask", tailwind=False)

        self.assertTrue((templates / "welcome.html").exists())

    def test_django_serves_its_own_until_the_project_has_urls(self):
        templates = self.prepare("django", tailwind=False)

        self.assertFalse((templates / "welcome.html").exists())

    def test_the_layout_and_the_page_fit_together(self):
        """The one shape the engine actually fills: @block, and {{ slot }}."""
        from pyblade.engine.renderer import PyBlade

        templates = self.prepare("flask", tailwind=False)
        html = PyBlade(dirs=[str(templates)]).render_file("welcome", {"framework": "Flask"})

        self.assertIn("<h1>It works.</h1>", html)
        self.assertIn("rendered by your Flask application", html)
        self.assertIn("<title>PyBlade</title>", html)


class TestRunningWhatWasScaffolded(unittest.TestCase):
    def test_each_framework_has_a_development_server_to_run(self):
        dev = importlib.import_module("pyblade.cli.commands.dev")

        self.assertEqual(
            dev.SERVERS["flask"]("127.0.0.1", "8000"),
            ["flask", "--app", "app", "run", "--debug", "--host", "127.0.0.1", "--port", "8000"],
        )
        self.assertEqual(
            dev.SERVERS["fastapi"]("127.0.0.1", "8000"),
            ["uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
        )

    def test_the_module_it_runs_is_the_one_init_wrote(self):
        dev = importlib.import_module("pyblade.cli.commands.dev")

        self.assertIn("app", dev.SERVERS["flask"]("h", "p"))
        self.assertIn("main:app", dev.SERVERS["fastapi"]("h", "p"))
        self.assertEqual(init.APPLICATION_FILE["flask"], "app.py")
        self.assertEqual(init.APPLICATION_FILE["fastapi"], "main.py")
