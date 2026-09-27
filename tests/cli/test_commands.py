"""The commands a project writes for itself, and the ones that write them.

A command is a class, and a project's own are found in a folder of its own. What
has to hold is that one written by `make:command` runs as it was written, from
wherever PyBlade is started, and that what it is run with reaches it the way its
author declared it.
"""

import importlib
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from pyblade.cli import BaseCommand, main
from pyblade.config import config

make_command = importlib.import_module("pyblade.cli.commands.make:command")
make_component = importlib.import_module("pyblade.cli.commands.make:component")


class InADirectory(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

    def written(self):
        return sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_file())


class Greet(BaseCommand):
    name = "greet"

    seen = {}

    def config(self):
        self.add_argument("who")
        self.add_option("-t", "--title", help="How to address them", default="Ms")
        self.add_flag("--dry-run", help="Say nothing")

    def handle(self, **kwargs):
        Greet.seen = {
            "argument": self.argument("who"),
            "option": self.option("title"),
            "flag": self.option("--dry-run"),
            "get": self.get("dry-run"),
            "missing": self.get("nothing", "fallback"),
            "argument_as_option": self.option("who"),
            "option_as_argument": self.argument("title"),
        }


class TestReadingWhatTheCommandWasRunWith(unittest.TestCase):
    def run_greet(self, *arguments):
        result = CliRunner().invoke(Greet.create_click_command(), list(arguments))
        self.assertEqual(result.exit_code, 0, result.output)

        return Greet.seen

    def test_an_argument_is_read_by_its_name(self):
        self.assertEqual(self.run_greet("Ada")["argument"], "Ada")

    def test_an_option_is_read_by_its_long_name_and_keeps_its_default(self):
        self.assertEqual(self.run_greet("Ada")["option"], "Ms")
        self.assertEqual(self.run_greet("Ada", "-t", "Dr")["option"], "Dr")

    def test_a_flag_is_read_however_its_name_is_written(self):
        seen = self.run_greet("Ada", "--dry-run")

        self.assertTrue(seen["flag"])
        self.assertTrue(seen["get"])

    def test_get_falls_back_for_what_was_not_given(self):
        self.assertEqual(self.run_greet("Ada")["missing"], "fallback")

    def test_an_argument_is_not_an_option_and_the_other_way_round(self):
        seen = self.run_greet("Ada")

        self.assertIsNone(seen["argument_as_option"])
        self.assertIsNone(seen["option_as_argument"])


class TestMakingACommand(InADirectory):
    def make(self, name, **options):
        make_command.Command().handle(name=name, **options)

    def test_it_goes_in_the_commands_directory_of_the_project(self):
        self.make("report:send")

        self.assertEqual(self.written(), ["management/commands/report:send.py"])

    def test_the_directory_is_the_one_the_project_says(self):
        with config.override({"paths.commands": "tools/commands"}):
            self.make("report")

        self.assertEqual(self.written(), ["tools/commands/report.py"])

    def test_it_is_written_from_the_root_of_the_project_wherever_it_is_run_from(self):
        (self.root / "pyblade.toml").write_text('[stack]\nframework = "flask"\n')
        (self.root / "app").mkdir()
        os.chdir(self.root / "app")

        with config.override({"paths.root": self.root}):
            self.make("report")

        self.assertTrue((self.root / "management/commands/report.py").exists())
        self.assertFalse((self.root / "app/management").exists())

    def test_it_does_not_write_over_a_command_unless_told_to(self):
        self.make("report", description="First")
        self.make("report", description="Second")

        self.assertIn("First", (self.root / "management/commands/report.py").read_text())

        self.make("report", description="Second", force=True)

        self.assertIn("Second", (self.root / "management/commands/report.py").read_text())


class TestRunningACommandTheProjectWrote(InADirectory):
    def setUp(self):
        super().setUp()

        self.cached = dict(main._CACHED_COMMANDS)
        self.path = list(sys.path)
        self.known = set(main.cli.commands)
        self.modules = set(sys.modules)

        self.addCleanup(self.forget)

    def forget(self):
        main._CACHED_COMMANDS.clear()
        main._CACHED_COMMANDS.update(self.cached)
        sys.path[:] = self.path

        for name in set(main.cli.commands) - self.known:
            del main.cli.commands[name]

        for name in set(sys.modules) - self.modules:
            del sys.modules[name]

    def test_a_command_made_by_make_command_is_found_and_runs(self):
        make_command.Command().handle(name="report:send", description="Send the report")

        # The way a command is started outside Django: nothing has put the
        # project on the path, and it is not where the command is run from
        os.chdir(tempfile.gettempdir())
        sys.path[:] = [entry for entry in sys.path if Path(entry or ".").resolve() != self.root]

        with config.override({"paths.root": self.root}):
            main.load_custom_commands()

        self.assertIn("report:send", main.cli.commands)
        self.assertEqual(main.cli.commands["report:send"].help, "Send the report")

        result = CliRunner().invoke(main.cli, ["report:send"])
        self.assertEqual(result.exit_code, 0, result.output)

    def test_a_command_with_arguments_and_options_is_run_with_them(self):
        commands = self.root / "management/commands"
        commands.mkdir(parents=True)
        (commands / "shout.py").write_text(
            "from pyblade.cli import BaseCommand\n\n\n"
            "class Command(BaseCommand):\n"
            '    """Shout it."""\n\n'
            '    name = "shout"\n\n'
            "    def config(self):\n"
            '        self.add_argument("word")\n'
            '        self.add_flag("--loud", help="Louder")\n\n'
            "    def handle(self, **kwargs):\n"
            '        self.print(kwargs["word"].upper() + ("!" if self.option("loud") else ""))\n'
        )

        with config.override({"paths.root": self.root}):
            main.load_custom_commands()

        result = CliRunner().invoke(main.cli, ["shout", "hey", "--loud"])

        self.assertIn("HEY!", result.output)


class TestMakingAComponent(InADirectory):
    def make(self, name, **options):
        make_component.Command().handle(name=name, **options)

    def test_a_component_is_a_template(self):
        self.make("Alert")

        self.assertEqual(self.written(), ["components/alert.html"])

    def test_it_is_not_written_over_unless_told_to(self):
        self.make("alert")
        (self.root / "components/alert.html").write_text("mine")

        self.make("alert")
        self.assertEqual((self.root / "components/alert.html").read_text(), "mine")

        self.make("alert", force=True)
        self.assertNotEqual((self.root / "components/alert.html").read_text(), "mine")

    def test_live_makes_a_live_component(self):
        self.make("counter", live=True)

        self.assertEqual(self.written(), ["components/counter/counter.html", "components/counter/counter.py"])

    def test_inline_makes_a_live_component_without_a_template(self):
        self.make("counter", inline=True)

        self.assertEqual(self.written(), ["components/counter/counter.py"])
        self.assertIn("render_inline", (self.root / "components/counter/counter.py").read_text())

    def test_force_reaches_a_live_component_too(self):
        self.make("counter", live=True)
        (self.root / "components/counter/counter.py").write_text("mine")

        self.make("counter", live=True)
        self.assertEqual((self.root / "components/counter/counter.py").read_text(), "mine")

        self.make("counter", live=True, force=True)
        self.assertNotEqual((self.root / "components/counter/counter.py").read_text(), "mine")
