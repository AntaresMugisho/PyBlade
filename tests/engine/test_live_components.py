import shutil
import tempfile
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.engine.nodes import ComponentNode


class ComponentResolutionTestCase(unittest.TestCase):
    """How a component name is mapped to the files it is made of."""

    def setUp(self):
        self.components_dir = Path(tempfile.mkdtemp())

        self._saved_components_dir = settings._data.get("components_dir")
        settings._data["components_dir"] = str(self.components_dir)

        self.node = ComponentNode("'unused'")

    def tearDown(self):
        if self._saved_components_dir is None:
            settings._data.pop("components_dir", None)
        else:
            settings._data["components_dir"] = self._saved_components_dir
        shutil.rmtree(self.components_dir, ignore_errors=True)

    def _write(self, name, content=""):
        """Write a component file, `name` using dot notation for the folders."""
        parts = name.split(".")
        path = self.components_dir.joinpath(*parts[:-2]) / ".".join(parts[-2:])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_html_file_alone_is_a_static_component(self):
        html = self._write("button.html", "<button>Go</button>")

        self.assertEqual(self.node._resolve_component("button"), {
            "type": "static",
            "name": "button",
            "html": html,
            "python": None,
        })

    def test_python_file_alone_is_a_live_component(self):
        python = self._write("live.counter.py")

        component = self.node._resolve_component("live.counter")

        self.assertEqual(component["type"], "live")
        self.assertEqual(component["python"], python)
        self.assertIsNone(component["html"])

    def test_python_file_wins_over_an_html_file_of_the_same_name(self):
        """A live component may keep its template beside its class."""
        python = self._write("live.counter.py")
        html = self._write("live.counter.html", "<div>0</div>")

        component = self.node._resolve_component("live.counter")

        self.assertEqual(component["type"], "live")
        self.assertEqual(component["python"], python)
        self.assertEqual(component["html"], html)

    def test_directory_based_live_component(self):
        python = self._write("counter.counter.py")
        html = self._write("counter.counter.html", "<div>0</div>")

        component = self.node._resolve_component("counter")

        self.assertEqual(component["type"], "live")
        self.assertEqual(component["python"], python)
        self.assertEqual(component["html"], html)

    def test_unknown_component(self):
        self.assertIsNone(self.node._resolve_component("nowhere"))


class TestInlineRendering(unittest.TestCase):
    """A live component writing its template inline rather than in a file."""

    def _component(self, template_string, **state):
        from pyblade.live import Component

        class Inline(Component):
            template_name = "inline"

            def render(self):
                return self.render_inline(template_string, context={})

        component = Inline("pb-test")
        for name, value in state.items():
            setattr(component, name, value)

        return component

    def test_renders_its_template_string(self):
        component = self._component("<div>{{ count }}</div>", count=3)

        self.assertEqual(component.render(), '<div pb:id="pb-test">3</div>')

    def test_keeps_the_rendered_output(self):
        component = self._component("<div>{{ count }}</div>", count=3)
        component.render()

        self.assertEqual(component._rendered, '<div pb:id="pb-test">3</div>')

    def test_keeps_the_attributes_of_the_root_element(self):
        component = self._component('<div class="counter" id="c">{{ count }}</div>', count=1)

        self.assertEqual(component.render(), '<div class="counter" id="c" pb:id="pb-test">1</div>')

    def test_root_element_holding_regex_characters(self):
        component = self._component('<div class="w-[50%] p-2.5 (x)">{{ count }}</div>', count=1)

        self.assertEqual(component.render(), '<div class="w-[50%] p-2.5 (x)" pb:id="pb-test">1</div>')

    def test_self_closing_root_element(self):
        component = self._component('<img src="{{ src }}" />', src="/a.png")

        self.assertEqual(component.render(), '<img src="/a.png" pb:id="pb-test"/>')


class TestImportOrder(unittest.TestCase):
    """The engine and the live package must not depend on each other at import time."""

    def _import(self, *modules):
        import subprocess
        import sys

        source = "".join(f"import {module}\n" for module in modules)
        result = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True)
        return result

    def test_importing_the_engine_first(self):
        result = self._import("pyblade.engine.nodes", "pyblade.live")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_importing_the_live_package_first(self):
        result = self._import("pyblade.live", "pyblade.engine.nodes")

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
