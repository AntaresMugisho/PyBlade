"""Finding a component by its path, and saying why it could not be found.

The registry imports the module a component lives in. That can fail for reasons
that have nothing to do with the component being missing -- an import in its own
file that points nowhere, above all -- and the developer needs to be told which,
not that the component "could not be resolved".
"""

import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from pyblade.live.registry import ComponentNotFound, registry

PREFIX = "registry_probe_"


class RegistryTestCase(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        sys.path.insert(0, str(self.root))

        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.addCleanup(self.forget)

    def forget(self):
        sys.path.remove(str(self.root))

        for name in [name for name in sys.modules if name.startswith(PREFIX)]:
            del sys.modules[name]

        for path in [path for path in registry._components if path.startswith(PREFIX)]:
            del registry._components[path]

    def module(self, name, source=""):
        (self.root / f"{PREFIX}{name}.py").write_text(textwrap.dedent(source))

        return f"{PREFIX}{name}"

    def refusal(self, class_path):
        with self.assertRaises(ComponentNotFound) as refused:
            registry.get(class_path)

        return refused.exception


class TestFindingAComponent(RegistryTestCase):
    def test_a_component_is_found_by_its_path(self):
        module = self.module("found", "class Thing:\n    pass\n")

        self.assertEqual(registry.get(f"{module}.Thing").__name__, "Thing")


class TestSayingWhyNot(RegistryTestCase):
    def test_a_module_that_does_not_exist_is_named(self):
        refused = self.refusal(f"{PREFIX}nowhere.Thing")

        self.assertIn(f"{PREFIX}nowhere.Thing", str(refused))
        self.assertIn(f"No module named '{PREFIX}nowhere'", str(refused))

    def test_an_import_that_fails_inside_the_component_is_named(self):
        # The module is there; what it imports is not
        module = self.module("broken", "from pyblade.decorators import computed\n\nclass Thing:\n    pass\n")

        refused = self.refusal(f"{module}.Thing")

        self.assertIn("No module named 'pyblade.decorators'", str(refused))

    def test_a_class_the_module_does_not_hold_is_named(self):
        module = self.module("empty", "x = 1\n")

        self.assertIn("Thing", str(self.refusal(f"{module}.Thing")))

    def test_a_path_with_no_class_in_it_is_refused(self):
        refused = self.refusal("nodots")

        self.assertIn("nodots", str(refused))

    def test_the_error_that_was_hit_is_kept_as_the_cause(self):
        module = self.module("cause", "import registry_probe_not_there\n")

        refused = self.refusal(f"{module}.Thing")

        self.assertIsInstance(refused.__cause__, ImportError)

    def test_it_is_still_a_value_error_for_whatever_caught_one_before(self):
        self.assertIsInstance(self.refusal(f"{PREFIX}nowhere.Thing"), ValueError)


if __name__ == "__main__":
    unittest.main()
