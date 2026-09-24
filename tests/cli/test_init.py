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
