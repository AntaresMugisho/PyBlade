"""Where `pyblade make:live` puts a new live component.

A component is two files that belong together, a class and the template it
renders, and both live in the components directory. Whether they sit in a
folder of their own or side by side is the project's to say -- and either way
the engine has to be able to find the template from the class, which it does by
reading where the class sits relative to the components directory.
"""

import importlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import config
from pyblade.utils import pascal_to_snake

make_live = importlib.import_module("pyblade.cli.commands.make:live")


class MakeLiveTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)

        self.command = make_live.Command()

    def make(self, name, own_folder=True, **options):
        with config.override({"live_components.own_folder": own_folder}):
            self.command.handle(name=name, **options)

    def written(self):
        return sorted(str(path.relative_to(self.root)) for path in self.root.rglob("*") if path.is_file())


class TestAFolderOfItsOwn(MakeLiveTestCase):
    """The default: somewhere for the stylesheet and the partials to go later."""

    def test_the_class_and_the_template_go_in_a_folder_named_after_it(self):
        self.make("Counter")

        self.assertEqual(self.written(), ["components/counter/counter.html", "components/counter/counter.py"])

    def test_a_dotted_name_puts_that_folder_where_the_name_says(self):
        self.make("shop.CartTotal")

        self.assertEqual(
            self.written(),
            ["components/shop/cart_total/cart_total.html", "components/shop/cart_total/cart_total.py"],
        )


class TestSideBySide(MakeLiveTestCase):
    def test_the_two_files_sit_in_the_components_directory(self):
        self.make("Counter", own_folder=False)

        self.assertEqual(self.written(), ["components/counter.html", "components/counter.py"])

    def test_a_dotted_name_still_says_where(self):
        self.make("shop.CartTotal", own_folder=False)

        self.assertEqual(self.written(), ["components/shop/cart_total.html", "components/shop/cart_total.py"])


class TestWhatTheEngineWillMakeOfIt(MakeLiveTestCase):
    """The template is found from where the class sits, so the two must agree.

    `LiveComponent._locate` takes the class file, makes it relative to the
    components directory and joins the parts with dots; the loader then turns
    that back into a path. Whatever layout was chosen, that round trip has to
    land on the template that was just written.
    """

    def located(self, python_file):
        relative = Path(python_file).with_suffix("").relative_to("components")

        return ".".join(relative.parts)

    def test_a_component_in_its_own_folder_is_found(self):
        self.make("Counter")

        name = self.located("components/counter/counter.py")

        self.assertEqual(name, "counter.counter")
        self.assertTrue((self.root / "components" / Path(*name.split("."))).with_suffix(".html").exists())

    def test_a_component_beside_its_template_is_found(self):
        self.make("Counter", own_folder=False)

        name = self.located("components/counter.py")

        self.assertEqual(name, "counter")
        self.assertTrue((self.root / "components" / Path(*name.split("."))).with_suffix(".html").exists())


class TestNamingAComponent(unittest.TestCase):
    def test_a_dotted_name_is_a_path_and_each_part_is_converted_on_its_own(self):
        """Run together, the dot reads as the character before a word."""
        self.assertEqual(pascal_to_snake("shop.CartTotal"), "shop.cart_total")
        self.assertEqual(pascal_to_snake("shop.admin.UserRow"), "shop.admin.user_row")

    def test_a_plain_name_is_unchanged_by_that(self):
        self.assertEqual(pascal_to_snake("CartTotal"), "cart_total")
        self.assertEqual(pascal_to_snake("Counter"), "counter")
        self.assertEqual(pascal_to_snake("cart-total"), "cart_total")
