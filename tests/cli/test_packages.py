"""Which tool a project installs things with, and how it is asked.

PyBlade does not own the environment it runs in. Somebody has already chosen
how this project keeps its dependencies, and the whole point of this module is
to read that choice off the project rather than assume it -- because assuming
it is how a package ends up somewhere nobody is looking, or how an install
fails outright on a Debian machine that refuses to let pip touch the system
Python.
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pyblade.cli import packages
from pyblade.config import config


class PackagesTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def installed(self, *names):
        """Say which tools this machine has, so a test does not depend on it."""
        return mock.patch.object(packages.shutil, "which", lambda name: name if name in names else None)


class TestWhatTheProjectShows(PackagesTestCase):
    def test_a_lock_file_says_which_manager_is_in_use(self):
        (self.root / "poetry.lock").touch()

        with self.installed("poetry", "uv", "pip"):
            self.assertEqual(packages.detect_python_manager(self.root), "poetry")

    def test_a_tool_table_in_the_pyproject_says_so_too(self):
        (self.root / "pyproject.toml").write_text('[project]\nname = "x"\n\n[tool.poetry]\nname = "x"\n')

        with self.installed("poetry", "uv"):
            self.assertEqual(packages.detect_python_manager(self.root), "poetry")

    def test_a_pyproject_with_nothing_of_theirs_in_it_says_nothing(self):
        (self.root / "pyproject.toml").write_text('[project]\nname = "x"\n')

        with self.installed("poetry"):
            self.assertEqual(packages._shown_by(self.root, packages.PYTHON_MANAGERS), "")

    def test_a_lock_file_for_a_tool_the_machine_has_not_got_is_not_chosen(self):
        """Naming a tool that cannot be run would only fail later, less clearly."""
        (self.root / "poetry.lock").touch()

        with self.installed("uv"):
            self.assertEqual(packages._shown_by(self.root, packages.PYTHON_MANAGERS), "")

    def test_the_javascript_side_is_read_the_same_way(self):
        (self.root / "pnpm-lock.yaml").touch()

        with self.installed("pnpm", "npm"):
            self.assertEqual(packages.detect_js_manager(self.root), "pnpm")


class TestWhenTheProjectShowsNothing(PackagesTestCase):
    def test_pip_is_used_inside_a_virtualenv(self):
        with self.installed("pip"), mock.patch.object(packages, "in_virtualenv", lambda: True):
            self.assertEqual(packages.detect_python_manager(self.root), "pip")

    def test_pip_is_not_used_outside_one(self):
        """Writing into the system Python is not PyBlade's to do."""
        with self.installed("pip"), mock.patch.object(packages, "in_virtualenv", lambda: False):
            self.assertEqual(packages.detect_python_manager(self.root), "")

    def test_a_virtualenv_wins_over_a_manager_that_is_merely_installed(self):
        """Using uv here would change a project that never asked for it."""
        with self.installed("uv", "pip"), mock.patch.object(packages, "in_virtualenv", lambda: True):
            self.assertEqual(packages.detect_python_manager(self.root), "pip")

    def test_npm_comes_before_the_others_for_javascript(self):
        """It is the one that comes with Node, not the one somebody happens to have."""
        with self.installed("npm", "bun", "pnpm"):
            self.assertEqual(packages.detect_js_manager(self.root), "npm")

    def test_and_something_else_is_used_when_there_is_no_npm(self):
        with self.installed("bun"):
            self.assertEqual(packages.detect_js_manager(self.root), "bun")

    def test_nothing_at_all_is_an_answer_too(self):
        with self.installed(), mock.patch.object(packages, "in_virtualenv", lambda: False):
            self.assertEqual(packages.detect_python_manager(self.root), "")
            self.assertEqual(packages.detect_js_manager(self.root), "")


class TestWhatTheProjectItselfSaid(PackagesTestCase):
    def test_pyblade_toml_beats_anything_that_was_worked_out(self):
        (self.root / "uv.lock").touch()

        with self.installed("uv", "poetry"), config.override({"stack.package_manager": "poetry"}):
            self.assertEqual(packages.python_manager(self.root), "poetry")

    def test_and_is_only_worked_out_when_the_project_said_nothing(self):
        (self.root / "uv.lock").touch()

        with self.installed("uv"):
            self.assertEqual(packages.python_manager(self.root), "uv")

    def test_the_javascript_side_is_said_separately(self):
        with self.installed("npm", "pnpm"), config.override({"stack.js_package_manager": "pnpm"}):
            self.assertEqual(packages.js_manager(self.root), "pnpm")


class TestHowAManagerIsAsked(unittest.TestCase):
    def test_each_one_is_asked_the_way_it_expects(self):
        self.assertEqual(packages.python_install_command("uv", ["django"]), ["uv", "add", "django"])
        self.assertEqual(packages.python_install_command("poetry", ["django"]), ["poetry", "add", "django"])
        self.assertEqual(packages.python_install_command("pipenv", ["django"]), ["pipenv", "install", "django"])
        self.assertEqual(packages.js_install_command("npm", ["tailwindcss"]), ["npm", "install", "tailwindcss"])
        self.assertEqual(packages.js_install_command("pnpm", ["tailwindcss"]), ["pnpm", "add", "tailwindcss"])

    def test_pip_is_asked_through_the_interpreter_that_is_running(self):
        """Never whichever `pip` happens to be first on PATH."""
        command = packages.python_install_command("pip", ["django"])

        self.assertEqual(command, [sys.executable, "-m", "pip", "install", "django"])
        self.assertNotIn("pip3", command)

    def test_a_manager_there_is_no_way_to_ask_gives_back_nothing(self):
        self.assertIsNone(packages.python_install_command("", ["django"]))
        self.assertIsNone(packages.js_install_command("", ["tailwindcss"]))

    def test_a_command_can_be_shown_the_way_somebody_would_type_it(self):
        typed = packages.as_typed(packages.python_install_command("pip", ["django"]))

        self.assertEqual(typed, "python -m pip install django")

    def test_several_packages_are_asked_for_at_once(self):
        command = packages.js_install_command("npm", ["tailwindcss", "@tailwindcss/cli"])

        self.assertEqual(command, ["npm", "install", "tailwindcss", "@tailwindcss/cli"])


class TestBringingThingsUpToDate(unittest.TestCase):
    def test_each_manager_is_asked_the_way_it_expects(self):
        self.assertEqual(packages.python_upgrade_command("uv", ["pyblade"]), ["uv", "add", "--upgrade", "pyblade"])
        self.assertEqual(packages.python_upgrade_command("poetry", ["pyblade"]), ["poetry", "update", "pyblade"])
        self.assertEqual(packages.python_upgrade_command("pipenv", ["pyblade"]), ["pipenv", "update", "pyblade"])

    def test_pip_upgrades_through_the_interpreter_that_is_running(self):
        self.assertEqual(
            packages.python_upgrade_command("pip", ["pyblade"]),
            [sys.executable, "-m", "pip", "install", "--upgrade", "pyblade"],
        )

    def test_a_manager_there_is_no_way_to_ask_gives_back_nothing(self):
        self.assertIsNone(packages.python_upgrade_command("", ["pyblade"]))


class TestRunningAToolTheProjectInstalled(unittest.TestCase):
    """Tailwind is run out of the project's node_modules, not off the machine."""

    def test_each_manager_has_its_own_way_of_running_one(self):
        self.assertEqual(
            packages.js_run_command("npm", ["tailwindcss", "-i", "in"]),
            ["npx", "tailwindcss", "-i", "in"],
        )
        self.assertEqual(packages.js_run_command("pnpm", ["tailwindcss"]), ["pnpm", "exec", "tailwindcss"])
        self.assertEqual(packages.js_run_command("yarn", ["tailwindcss"]), ["yarn", "exec", "tailwindcss"])
        self.assertEqual(packages.js_run_command("bun", ["tailwindcss"]), ["bunx", "tailwindcss"])

    def test_a_manager_there_is_no_way_to_ask_gives_back_nothing(self):
        self.assertIsNone(packages.js_run_command("", ["tailwindcss"]))
