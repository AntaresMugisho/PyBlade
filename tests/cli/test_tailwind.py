"""Setting a project up to build a Tailwind stylesheet.

Tailwind is not a stylesheet you link. It reads the templates, finds the
classes actually used and writes a stylesheet holding only those, so a project
using it has a stylesheet it writes, the templates Tailwind reads, and the
stylesheet Tailwind builds -- and something has to run the build. What is
tested here is that all three end up pointing at each other.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.cli import tailwind
from pyblade.config import config


class TailwindTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def configure(self, sources=("templates", "components")):
        return tailwind.configure(self.root, config.paths.stubs, list(sources))


class TestTheStylesheetAProjectWrites(TailwindTestCase):
    def test_it_imports_tailwind(self):
        self.assertIn('@import "tailwindcss";', tailwind.stylesheet("templates"))

    def test_it_says_where_the_classes_are_used(self):
        """Tailwind can work it out, but only from the directory it is run in."""
        written = tailwind.stylesheet("templates", "components")

        self.assertIn('@source "../../templates";', written)
        self.assertIn('@source "../../components";', written)

    def test_the_sources_are_written_relative_to_the_stylesheet(self):
        """Which is where Tailwind reads them from, not the project root."""
        depth = len(tailwind.INPUT.parent.parts)

        self.assertIn(f'@source "{"/".join([".."] * depth)}/templates";', tailwind.stylesheet("templates"))

    def test_configuring_writes_it_where_the_build_reads_it(self):
        self.configure()

        self.assertTrue((self.root / tailwind.INPUT).exists())
        self.assertIn("-i", tailwind.build_command("npm"))
        self.assertIn(tailwind.INPUT.as_posix(), tailwind.build_command("npm"))


class TestWhatConfiguringDoes(TailwindTestCase):
    def test_it_says_what_it_did(self):
        done = self.configure()

        self.assertTrue(any(tailwind.INPUT.name in line for line in done))
        self.assertTrue(any("layout.html" in line for line in done))

    def test_it_writes_a_layout_that_links_the_built_stylesheet(self):
        self.configure()

        layout = (self.root / "templates" / "layout.html").read_text()

        self.assertIn(tailwind.OUTPUT.name, layout)

    def test_a_project_that_already_has_a_layout_keeps_the_one_it_has(self):
        (self.root / "templates").mkdir()
        (self.root / "templates" / "layout.html").write_text("<html>mine</html>")

        self.configure()

        self.assertEqual((self.root / "templates" / "layout.html").read_text(), "<html>mine</html>")

    def test_the_installed_packages_are_kept_out_of_the_repository(self):
        self.configure()

        self.assertIn("node_modules/", (self.root / ".gitignore").read_text())

    def test_an_existing_gitignore_is_added_to_rather_than_replaced(self):
        (self.root / ".gitignore").write_text("*.pyc\n")

        self.configure()
        written = (self.root / ".gitignore").read_text()

        self.assertIn("*.pyc", written)
        self.assertIn("node_modules/", written)

    def test_a_gitignore_that_already_says_so_is_left_alone(self):
        (self.root / ".gitignore").write_text("node_modules/\n")

        self.assertFalse(tailwind.ignore_node_modules(self.root))
        self.assertEqual((self.root / ".gitignore").read_text(), "node_modules/\n")


class TestBuildingTheStylesheet(TailwindTestCase):
    def test_the_build_reads_the_input_and_writes_the_output(self):
        command = tailwind.build_command("npm")

        self.assertEqual(
            command,
            ["npx", "@tailwindcss/cli", "-i", tailwind.INPUT.as_posix(), "-o", tailwind.OUTPUT.as_posix()],
        )

    def test_watching_is_the_same_build_that_does_not_stop(self):
        self.assertEqual(tailwind.build_command("npm", watch=True)[-1], "--watch")

    def test_it_is_run_through_the_project_s_own_package_manager(self):
        """So it is this project's Tailwind, not whichever is on the machine."""
        self.assertEqual(tailwind.build_command("pnpm")[:2], ["pnpm", "exec"])
        self.assertEqual(tailwind.build_command("bun")[0], "bunx")

    def test_there_is_no_build_without_something_to_run_it(self):
        self.assertIsNone(tailwind.build_command(""))


class TestWhetherAProjectUsesIt(TailwindTestCase):
    def test_a_project_with_no_stylesheet_does_not(self):
        self.assertFalse(tailwind.is_configured(self.root))

    def test_and_one_that_has_been_configured_does(self):
        self.configure()

        self.assertTrue(tailwind.is_configured(self.root))
