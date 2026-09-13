"""A component that keeps the page waiting for nothing.

A component written @lazy does none of its work while the page is being built:
it writes a skeleton of itself, and the page asks for it again as soon as it has
loaded -- or once it has been scrolled to, where it says so. What mount() was to
be given travels in the signed snapshot, so the work happens once, later, with
the same arguments it would have had.
"""

import json
import unittest

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import lazy


def component(name="Lazy", **body):
    """A component of the given body, whose render says what it holds."""
    body.setdefault("render", lambda self: self.render_inline(
        "<div>Loaded: {{ greeting }}</div>", context={}
    ))
    body.setdefault("greeting", "")

    return type(name, (LiveComponent,), body)


class TestTheFirstPass(unittest.TestCase):
    """Nothing of a lazy component is done while the page is being built."""

    def setUp(self):
        self.mounted = []

        self.cls = lazy(component(
            mount=lambda self: self.mounted.append(True) or setattr(self, "greeting", "done"),
            mounted=self.mounted,
        ))

    def test_it_does_not_mount(self):
        self.cls.render_initial()

        self.assertEqual(self.mounted, [])

    def test_it_does_not_render_itself(self):
        self.assertNotIn("Loaded:", self.cls.render_initial())

    def test_what_it_writes_is_a_skeleton(self):
        self.assertIn("pb-skeleton", self.cls.render_initial())

    def test_the_skeleton_is_the_component(self):
        """It carries the id and the snapshot, so the page holds a component."""
        markup = self.cls.render_initial()

        self.assertIn("pb:id=", markup)
        self.assertIn("pb:snapshot=", markup)

    def test_the_page_is_told_to_ask_for_it(self):
        self.assertIn("pb:lazy", self.cls.render_initial())

    def test_it_is_asked_for_as_soon_as_the_page_has_loaded(self):
        self.assertIn('pb:lazy=""', self.cls.render_initial())

    def test_one_written_visible_waits_until_it_has_been_scrolled_to(self):
        cls = lazy(visible=True)(component())

        self.assertIn('pb:lazy="visible"', cls.render_initial())


class TestTheSkeletonItDraws(unittest.TestCase):
    def test_the_shape_and_the_lines_are_what_the_component_asked_for(self):
        cls = lazy(lines=4, shape="table")(component())

        markup = cls.render_initial()

        self.assertIn("pb-skeleton-table", markup)
        self.assertEqual(markup.count("pb-skeleton-row"), 4)

    def test_a_component_may_write_its_own(self):
        cls = lazy(component(
            placeholder=lambda self: self.render_inline("<div>Just a moment</div>", context={}),
        ))

        markup = cls.render_initial()

        self.assertIn("Just a moment", markup)
        self.assertNotIn("pb-skeleton", markup)

    def test_one_it_writes_is_still_the_component(self):
        cls = lazy(component(
            placeholder=lambda self: self.render_inline("<div>Just a moment</div>", context={}),
        ))

        markup = cls.render_initial()

        self.assertIn("pb:id=", markup)
        self.assertIn("pb:lazy", markup)

    def test_a_shape_it_cannot_draw_is_said_so_when_the_component_is_written(self):
        with self.assertRaises(ValueError):
            lazy(shape="tabel")(component())


class TestBeingAskedForAtTheCallSite(unittest.TestCase):
    """A component eager everywhere else may be lazy on one page."""

    def test_a_tag_written_lazy_makes_it_lazy(self):
        markup = component().render_initial({"lazy": True})

        self.assertIn("pb-skeleton", markup)

    def test_written_as_an_attribute_with_no_value_of_its_own(self):
        markup = component().render_initial({"lazy": "True"})

        self.assertIn("pb-skeleton", markup)

    def test_it_may_say_to_wait_until_it_is_seen(self):
        markup = component().render_initial({"lazy": "visible"})

        self.assertIn('pb:lazy="visible"', markup)

    def test_lazy_is_not_a_property_of_the_component(self):
        snapshot = json.loads(
            component().render_initial({"lazy": True}).split("pb:snapshot='")[1].split("'")[0]
            .replace("&#39;", "'").replace("&lt;", "<").replace("&amp;", "&")
        )

        self.assertNotIn("lazy", snapshot["state"])


class TestBeingLoaded(unittest.TestCase):
    """The work happens when the page comes back for it."""

    def _snapshot(self, markup):
        raw = markup.split("pb:snapshot='")[1].split("'")[0]

        return json.loads(raw.replace("&#39;", "'").replace("&lt;", "<").replace("&amp;", "&"))

    def test_it_mounts_and_renders_itself(self):
        cls = lazy(component(mount=lambda self: setattr(self, "greeting", "done")))
        snapshot = self._snapshot(cls.render_initial())

        answer = cls.update_component(
            snapshot["state"] | {"_id": snapshot["id"]}, "$lazy", [], mount=snapshot.get("mount"),
        )

        self.assertIn("Loaded: done", answer["html"])

    def test_it_mounts_with_what_it_was_given(self):
        cls = lazy(component(mount=lambda self, name: setattr(self, "greeting", name)))
        snapshot = self._snapshot(cls.render_initial({"name": "Antares"}))

        answer = cls.update_component(
            snapshot["state"] | {"_id": snapshot["id"]}, "$lazy", [], mount=snapshot.get("mount"),
        )

        self.assertIn("Loaded: Antares", answer["html"])

    def test_what_it_was_given_travels_with_the_snapshot(self):
        cls = lazy(component(mount=lambda self, name: setattr(self, "greeting", name)))

        snapshot = self._snapshot(cls.render_initial({"name": "Antares"}))

        self.assertEqual(snapshot["mount"], {"name": "Antares"})

    def test_once_loaded_it_is_not_waiting_any_more(self):
        cls = lazy(component(mount=lambda self: setattr(self, "greeting", "done")))
        snapshot = self._snapshot(cls.render_initial())

        answer = cls.update_component(
            snapshot["state"] | {"_id": snapshot["id"]}, "$lazy", [], mount=snapshot.get("mount"),
        )

        self.assertNotIn("mount", answer["snapshot"])
        self.assertNotIn("pb:lazy", answer["html"])

    def test_anything_else_asked_of_it_first_mounts_it_too(self):
        """A page that gets an event in before the load is not half a component."""
        cls = lazy(component(
            mount=lambda self: setattr(self, "greeting", "done"),
            shout=lambda self: setattr(self, "greeting", self.greeting.upper()),
        ))
        snapshot = self._snapshot(cls.render_initial())

        answer = cls.update_component(
            snapshot["state"] | {"_id": snapshot["id"]}, "shout", [], mount=snapshot.get("mount"),
        )

        self.assertIn("Loaded: DONE", answer["html"])

    def test_asking_twice_does_not_mount_twice(self):
        mounted = []
        cls = lazy(component(mount=lambda self: mounted.append(True), mounted=mounted))
        snapshot = self._snapshot(cls.render_initial())

        state = snapshot["state"] | {"_id": snapshot["id"]}
        answer = cls.update_component(state, "$lazy", [], mount=snapshot.get("mount"))
        cls.update_component(
            answer["snapshot"]["state"] | {"_id": snapshot["id"]},
            "$lazy", [], mount=answer["snapshot"].get("mount"),
        )

        self.assertEqual(len(mounted), 1)


class TestWhatCannotWait(unittest.TestCase):
    def test_something_that_cannot_travel_is_refused_where_it_is_written(self):
        cls = lazy(component(mount=lambda self, when: setattr(self, "greeting", str(when))))

        with self.assertRaises(TypeError) as caught:
            cls.render_initial({"when": object()})

        self.assertIn("lazy", str(caught.exception).lower())
        self.assertIn("when", str(caught.exception))


class TestTheRequestThePageMakes(unittest.TestCase):
    """What the page sends, through the endpoint it sends it to."""

    def setUp(self):
        from django.test import RequestFactory

        from pyblade.live.registry import registry

        self.requests = RequestFactory()
        self.registry = registry
        self.path = f"{__name__}.Waiting"

        registry.register(self.path, Waiting)

    def tearDown(self):
        self.registry._components.pop(self.path, None)

    def _snapshot(self):
        markup = Waiting.render_initial({"name": "Antares"})
        raw = markup.split("pb:snapshot='")[1].split("'")[0]
        snapshot = json.loads(raw.replace("&#39;", "'").replace("&lt;", "<").replace("&amp;", "&"))
        snapshot["class"] = self.path

        from pyblade.live.security import generate_checksum

        snapshot.pop("checksum")
        snapshot["checksum"] = generate_checksum(snapshot)

        return snapshot

    def test_asking_for_it_loads_it(self):
        from pyblade.live.views import update_component

        request = self.requests.post(
            "/pyblade/live/",
            data=json.dumps({"snapshot": self._snapshot(), "action": "$lazy", "params": []}),
            content_type="application/json",
        )

        answer = json.loads(update_component(request).content)

        self.assertIn("Loaded: Antares", answer["html"])
        self.assertNotIn("mount", answer["snapshot"])


@lazy
class Waiting(LiveComponent):
    greeting = ""

    def mount(self, name):
        self.greeting = name

    def render(self):
        return self.render_inline("<div>Loaded: {{ greeting }}</div>", context={})


import sys  # noqa: E402  -- the endpoint resolves the component by this module's name

sys.modules[__name__].Waiting = Waiting


class TestASkeletonOfItsOwn(unittest.TestCase):
    """A lazy component may show a template of its own while it waits."""

    def setUp(self):
        import shutil
        import tempfile
        from pathlib import Path

        from pyblade.config import settings
        from pyblade.engine import loader

        self.root = Path(tempfile.mkdtemp())
        self.templates = self.root / "templates"
        self.templates.mkdir()
        (self.templates / "skeletons").mkdir()
        (self.templates / "skeletons" / "figures.html").write_text(
            "<div class='my-own-skeleton'>Counting the figures</div>", encoding="utf-8"
        )

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.templates])

        self._saved = settings._data.get("templates_dir")
        settings._data["templates_dir"] = str(self.templates)

        self._cleanup = lambda: (
            setattr(loader._default_loader, "_template_dirs", self._saved_dirs),
            settings._data.__setitem__("templates_dir", self._saved)
            if self._saved is not None else settings._data.pop("templates_dir", None),
            shutil.rmtree(self.root, ignore_errors=True),
        )

    def tearDown(self):
        self._cleanup()

    def test_a_template_may_stand_in_for_it(self):
        cls = lazy(component(
            placeholder=lambda self: self.render_template("skeletons.figures"),
        ))

        markup = cls.render_initial()

        self.assertIn("Counting the figures", markup)
        self.assertNotIn("pb-skeleton-line", markup)

    def test_and_is_still_the_component_waiting(self):
        cls = lazy(component(
            placeholder=lambda self: self.render_template("skeletons.figures"),
        ))

        markup = cls.render_initial()

        self.assertIn("pb:id=", markup)
        self.assertIn("pb:snapshot=", markup)
        self.assertIn("pb:lazy", markup)
