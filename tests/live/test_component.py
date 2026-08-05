import os
import shutil
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from pyblade.config import settings
from pyblade.live import Component


class Counter(Component):
    """A component as a developer writes one."""

    count = 0
    label = "clicks"

    def increment(self, step=1):
        self.count += step

    def _secret(self):
        raise AssertionError("a private method must not be reachable")

    def render(self):
        return self.render_inline("<div>{{ count }}</div>", context={})


class TestComponentSurface(unittest.TestCase):
    """What of a component the client gets to see and to call."""

    def setUp(self):
        self.component = Counter("pb-test")

    def test_state_holds_the_properties_of_the_component(self):
        state = self.component._get_state()

        self.assertEqual(state["count"], 0)
        self.assertEqual(state["label"], "clicks")

    def test_state_leaves_out_the_machinery_of_the_base_class(self):
        state = self.component._get_state()

        for name in ("template_name", "_id", "_rendered"):
            self.assertNotIn(name, state)

    def test_state_leaves_out_private_properties(self):
        self.component._token = "secret"

        self.assertNotIn("_token", self.component._get_state())

    def test_state_leaves_out_methods(self):
        state = self.component._get_state()

        self.assertNotIn("increment", state)
        self.assertNotIn("render", state)

    def test_methods_hold_what_the_component_defines(self):
        self.assertIn("increment", self.component._get_methods())

    def test_methods_leave_out_the_machinery_of_the_base_class(self):
        methods = self.component._get_methods()

        for name in (
            "serialize",
            "deserialize",
            "render",
            "render_template",
            "render_inline",
            "get_template_name",
            "mount",
            "boot",
            "hydrate",
            "redirect",
            "navigate",
            "emit",
            "dispatch",
            "reset",
            "refresh",
            "set",
            "toggle",
        ):
            self.assertNotIn(name, methods)

    def test_methods_leave_out_private_methods(self):
        self.assertNotIn("_secret", self.component._get_methods())

    def test_the_snapshot_carries_nothing_but_the_state(self):
        snapshot = self.component.serialize()

        self.assertEqual(set(snapshot), {"id", "class", "state", "checksum"})
        self.assertEqual(snapshot["state"], {"count": 0, "label": "clicks"})


class TestClientActions(unittest.TestCase):
    """What the client is allowed to ask the component to do."""

    def _update(self, action, params=()):
        return Counter.update_component({"count": 0, "label": "clicks", "_id": "pb-test"}, action, list(params))

    def test_calling_a_method_of_the_component(self):
        result = self._update("increment")

        self.assertEqual(result["snapshot"]["state"]["count"], 1)

    def test_calling_a_method_with_parameters(self):
        result = self._update("increment", [5])

        self.assertEqual(result["snapshot"]["state"]["count"], 5)

    def test_calling_a_method_of_the_base_class_is_refused(self):
        for name in ("serialize", "render_template", "get_template_name", "redirect", "deserialize"):
            with self.subTest(method=name):
                with self.assertRaises(AttributeError):
                    self._update(name)

    def test_calling_a_private_method_is_refused(self):
        with self.assertRaises(AttributeError):
            self._update("_secret")

    def test_calling_an_unknown_method_is_refused(self):
        with self.assertRaises(NameError):
            self._update("nowhere")

    def test_setting_a_property_of_the_component(self):
        result = self._update("$set", ["count", 7])

        self.assertEqual(result["snapshot"]["state"]["count"], 7)

    def test_setting_a_property_of_the_base_class_is_refused(self):
        for name in ("template_name", "_id", "_rendered"):
            with self.subTest(property=name):
                with self.assertRaises(AttributeError):
                    self._update("$set", [name, "anything"])

    def test_refreshing_re_renders_without_calling_anything(self):
        result = self._update("$refresh")

        self.assertEqual(result["html"], "<div pb:id=\"pb-test\">0</div>")


class TestMagicActions(unittest.TestCase):
    """The actions a component calls on itself: reset, pull, toggle, set."""

    def _component(self, **body):
        body.setdefault("render", lambda self: self.render_inline("<div>{{ count }}</div>", context={}))
        return type("Magic", (Component,), {"count": 0, "label": "clicks", "tags": ["a"], **body})("pb-test")

    def test_reset_restores_a_property_to_what_the_class_declares(self):
        component = self._component()
        component.count = 12

        component.reset("count")

        self.assertEqual(component.count, 0)

    def test_reset_restores_every_property_when_given_no_name(self):
        component = self._component()
        component.count = 12
        component.label = "taps"

        component.reset()

        self.assertEqual(component._get_state(), {"count": 0, "label": "clicks", "tags": ["a"]})

    def test_reset_gives_back_a_value_of_its_own(self):
        """A declared list must not be shared between a component and its class."""
        component = self._component()
        component.tags.append("b")

        component.reset("tags")
        component.tags.append("c")

        self.assertEqual(component.tags, ["a", "c"])
        self.assertEqual(self._component().tags, ["a"])

    def test_reset_refuses_a_property_the_component_does_not_declare(self):
        component = self._component()

        with self.assertRaises(AttributeError):
            component.reset("nowhere")

    def test_reset_refuses_a_property_of_the_base_class(self):
        component = self._component()

        with self.assertRaises(AttributeError):
            component.reset("template_name")

    def test_pull_gives_the_value_back_and_resets_it(self):
        component = self._component()
        component.count = 9

        self.assertEqual(component.pull("count"), 9)
        self.assertEqual(component.count, 0)

    def test_toggle_turns_a_property_around(self):
        component = self._component(active=False)

        component.toggle("active")
        self.assertIs(component.active, True)

        component.toggle("active")
        self.assertIs(component.active, False)

    def test_set_updates_a_property(self):
        component = self._component()

        component.set("count", 4)

        self.assertEqual(component.count, 4)

    def test_set_runs_the_update_hooks(self):
        seen = []

        cls = type(
            "Hooked",
            (Component,),
            {
                "count": 0,
                "render": lambda self: self.render_inline("<div>{{ count }}</div>", context={}),
                "updating": lambda self, prop, value: seen.append(("updating", prop, value)),
                "updated": lambda self, prop, value: seen.append(("updated", prop, value)),
                "updated_count": lambda self, value: seen.append(("updated_count", value)),
            },
        )

        cls("pb-test").set("count", 3)

        self.assertEqual(
            seen,
            [("updating", "count", 3), ("updated", "count", 3), ("updated_count", 3)],
        )

    def test_set_refuses_a_property_of_the_base_class(self):
        component = self._component()

        with self.assertRaises(AttributeError):
            component.set("template_name", "elsewhere")

    def test_an_action_may_reset_the_component_from_the_client(self):
        cls = type(
            "Resettable",
            (Component,),
            {
                "count": 0,
                "render": lambda self: self.render_inline("<div>{{ count }}</div>", context={}),
                "clear": lambda self: self.reset("count"),
            },
        )

        result = cls.update_component({"count": 8, "_id": "pb-test"}, "clear")

        self.assertEqual(result["snapshot"]["state"]["count"], 0)


class TestInitialRendering(unittest.TestCase):
    """The first rendering of a component, on the server."""

    def _component(self, **body):
        body.setdefault("render", lambda self: self.render_inline("<div>{{ count }}</div>", context={}))
        return type("Greeter", (Component,), {"count": 0, **body})

    def test_class_defaults_make_up_the_initial_state(self):
        cls = self._component()

        cls.render_initial()

        self.assertEqual(cls("pb-test")._get_state(), {"count": 0})

    def test_properties_passed_to_the_component_reach_its_state(self):
        cls = self._component()

        html = cls.render_initial({"count": 5})

        self.assertIn("<div pb:id=", html)
        self.assertIn(">5<", html)

    def test_mount_receives_the_properties_it_declares(self):
        received = {}

        def mount(self, count=0, **kwargs):
            received.update({"count": count, "kwargs": kwargs})
            self.count = count * 2

        cls = self._component(mount=mount)

        html = cls.render_initial({"count": 3})

        self.assertEqual(received, {"count": 3, "kwargs": {}})
        self.assertIn(">6<", html)

    def test_mount_without_parameters_is_called_all_the_same(self):
        called = []

        cls = self._component(mount=lambda self: called.append(True))

        cls.render_initial({"count": 1})

        self.assertEqual(called, [True])

    def test_a_property_mount_does_not_declare_is_not_forced_on_it(self):
        """An unknown property still becomes state, it just is not a mount argument."""

        def mount(self, count=0):
            self.count = count

        cls = self._component(mount=mount)

        html = cls.render_initial({"count": 2, "extra": "kept"})

        self.assertIn('"extra": "kept"', html)

    def test_a_property_mount_consumes_is_not_state_of_its_own(self):
        """mount() turns what it is given into the state it decides on."""

        def mount(self, start=0):
            self.count = start

        cls = self._component(mount=mount)

        html = cls.render_initial({"start": 5})

        self.assertIn('"count": 5', html)
        self.assertNotIn('"start"', html)

    def test_properties_are_state_when_the_component_has_no_mount(self):
        """The base mount() takes **kwargs, which must not swallow the properties."""
        cls = self._component()

        html = cls.render_initial({"count": 5, "extra": "kept"})

        self.assertIn('"count": 5', html)
        self.assertIn('"extra": "kept"', html)

    def test_the_key_names_the_component_instead_of_a_generated_id(self):
        cls = self._component()

        html = cls.render_initial({"key": "counter-1"})

        self.assertIn('pb:id="counter-1"', html)

    def test_the_key_is_not_part_of_the_state(self):
        cls = self._component()

        html = cls.render_initial({"key": "counter-1"})

        self.assertNotIn('"key"', html)


class TestLiveComponentTag(unittest.TestCase):
    """Rendering a live component from the tag that calls it."""

    def setUp(self):
        from pyblade.engine import loader

        self.project_dir = Path(tempfile.mkdtemp())
        self.components_dir = self.project_dir / "components"
        (self.components_dir / "live").mkdir(parents=True)

        (self.components_dir / "__init__.py").write_text("")
        (self.components_dir / "live" / "__init__.py").write_text("")
        (self.components_dir / "live" / "counter.py").write_text(
            textwrap.dedent(
                """
                from pyblade import live

                class Counter(live.Component):
                    count = 0
                """
            )
        )
        (self.components_dir / "live" / "counter.html").write_text("<div>{{ count }}</div>")

        # The module of a component is read from where it lives, relative to the
        # working directory, so the project has to be the one we render from.
        self._saved_cwd = os.getcwd()
        os.chdir(self.project_dir)
        sys.path.insert(0, str(self.project_dir))

        self._saved_components_dir = settings._data.get("components_dir")
        settings._data["components_dir"] = "components"

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.project_dir])

    def tearDown(self):
        from pyblade.engine import loader
        from pyblade.live.registry import registry

        loader._default_loader._template_dirs = self._saved_dirs
        os.chdir(self._saved_cwd)
        sys.path.remove(str(self.project_dir))

        # Both caches key on the module path, which the next test reuses for a
        # component of its own, in a directory of its own
        registry._components.clear()
        for name in [name for name in sys.modules if name.startswith("components")]:
            del sys.modules[name]

        if self._saved_components_dir is None:
            settings._data.pop("components_dir", None)
        else:
            settings._data["components_dir"] = self._saved_components_dir
        shutil.rmtree(self.project_dir, ignore_errors=True)

    def _render(self, template):
        from pyblade.engine.processor import TemplateProcessor

        return TemplateProcessor().render(template, {})

    def test_the_component_renders_with_its_defaults(self):
        html = self._render('<pb-live.counter key="c1" />')

        self.assertIn('<div pb:id="c1">0</div>', html)

    def test_a_bound_attribute_reaches_the_component_as_a_value(self):
        html = self._render('<pb-live.counter :count="2 + 3" key="c1" />')

        self.assertIn('<div pb:id="c1">5</div>', html)
        self.assertIn('"count": 5', html)

    def test_a_quoted_attribute_reaches_the_component_as_text(self):
        html = self._render('<pb-live.counter count="5" key="c1" />')

        self.assertIn('"count": "5"', html)

    def test_the_state_of_a_live_component_is_declared_on_its_class(self):
        """@props declares the props of a static component, not the state of a live one.

        A live component holds what its class declares. @props written in its
        template still fills the context in, as it does anywhere, but what it
        declares is not state: it is not serialized and does not come back.
        """
        (self.components_dir / "live" / "counter.html").write_text(
            '@props({"label": "clicks", "count": 99})<div>{{ count }} {{ label }}</div>'
        )

        html = self._render('<pb-live.counter key="c1" />')

        # The class default wins over the one @props declares, and holds the state
        self.assertIn('<div pb:id="c1">0 clicks</div>', html)
        self.assertIn('"state": {"count": 0}', html)

    def test_a_bound_attribute_is_evaluated_in_the_context_of_the_caller(self):
        from pyblade.engine.processor import TemplateProcessor

        html = TemplateProcessor().render('<pb-live.counter :count="total" key="c1" />', {"total": 42})

        self.assertIn('"count": 42', html)


class TestTemplateName(unittest.TestCase):
    """The template of a component is found from where its class lives."""

    def setUp(self):
        self.components_dir = Path(tempfile.mkdtemp())
        (self.components_dir / "live").mkdir()

        self._saved_components_dir = settings._data.get("components_dir")
        settings._data["components_dir"] = str(self.components_dir)

        sys.path.insert(0, str(self.components_dir.parent))
        self.package = self.components_dir.name

    def tearDown(self):
        sys.path.remove(str(self.components_dir.parent))
        for name in [name for name in sys.modules if name.startswith(self.package)]:
            del sys.modules[name]

        if self._saved_components_dir is None:
            settings._data.pop("components_dir", None)
        else:
            settings._data["components_dir"] = self._saved_components_dir
        shutil.rmtree(self.components_dir, ignore_errors=True)

    def _write_component(self):
        (self.components_dir / "__init__.py").write_text("")
        (self.components_dir / "live" / "__init__.py").write_text("")
        (self.components_dir / "live" / "counter.py").write_text(
            textwrap.dedent(
                """
                from pyblade import live

                class Counter(live.Component):
                    count = 0
                """
            )
        )
        (self.components_dir / "live" / "counter.html").write_text("<div>{{ count }}</div>")

        import importlib

        module = importlib.import_module(f"{self.package}.live.counter")
        return module.Counter

    def test_derived_from_the_module_of_the_class(self):
        cls = self._write_component()

        self.assertEqual(cls("pb-test").get_template_name(), "live.counter")

    def test_an_explicit_template_name_wins(self):
        cls = self._write_component()
        cls.template_name = "live.other"

        self.assertEqual(cls("pb-test").get_template_name(), "live.other")

    def test_survives_a_round_trip_without_travelling_to_the_client(self):
        """The client never sends the template name back, so it must be found again."""
        cls = self._write_component()

        self.assertNotIn("template_name", cls("pb-test").serialize()["state"])
        self.assertEqual(cls.update_component({"count": 2, "_id": "pb-test"}, "$refresh")["html"],
                         '<div pb:id="pb-test">2</div>')


if __name__ == "__main__":
    unittest.main()
