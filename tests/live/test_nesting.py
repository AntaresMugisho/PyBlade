"""A live component written in the template of another.

The one written inside is not part of the markup of the one that writes it: it
has a state of its own and answers for itself. So it must keep the identity it
was given when its parent is rendered again, and the page must keep the one it
already holds rather than be handed a component started over from its defaults.
"""

import html
import json
import os
import re
import shutil
import sys
import tempfile
import textwrap
import unittest
from contextlib import ExitStack
from pathlib import Path

from pyblade.config import config
from pyblade.engine import loader
from pyblade.live.registry import registry


def snapshot_of(markup, pb_id):
    """Read back what the component of that id wrote on its root element."""
    match = re.search(rf"pb:id=\"{re.escape(pb_id)}\" pb:snapshot='([^']*)'", markup)

    return json.loads(html.unescape(match.group(1))) if match else None


def ids_in(markup):
    return re.findall(r'pb:id="([^"]+)"', markup)


class NestingTestCase(unittest.TestCase):
    """A project holding a parent component and the one it writes inside it.

    The module of a component is worked out from where its file lives, relative
    to the working directory, so these run from a project of their own.
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.components_dir = self.root / "components"
        self.components_dir.mkdir()
        (self.components_dir / "__init__.py").write_text("")

        self._saved_cwd = os.getcwd()
        os.chdir(self.root)
        sys.path.insert(0, str(self.root))

        self._saved_dirs = list(loader._default_loader._template_dirs)
        loader._default_loader.add_directories([self.root])

        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(config.override({"paths.templates": "templates", "paths.components": "components"}))

        self.write_child()
        self.write_parent()

    def tearDown(self):
        loader._default_loader._template_dirs = self._saved_dirs
        os.chdir(self._saved_cwd)
        sys.path.remove(str(self.root))

        # Both caches key on the module path, which the next test reuses for a
        # component of its own, in a directory of its own
        registry._components.clear()
        for name in [name for name in sys.modules if name.startswith("components")]:
            del sys.modules[name]

        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, name, content):
        path = self.components_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    def write_child(self, body="count = 0", template='<div id="child">{{ count }}</div>'):
        self._write(
            "child.py",
            f"from pyblade import LiveComponent\n\n\nclass Child(LiveComponent):\n"
            f"{textwrap.indent(textwrap.dedent(body).strip(), '    ')}\n",
        )
        self._write("child.html", template)

    def write_parent(
        self,
        template='<div id="parent">{{ title }}<pb-child /></div>',
        body="title = 'p'",
    ):
        self._write(
            "parent.py",
            f"from pyblade import LiveComponent\n\n\nclass Parent(LiveComponent):\n"
            f"{textwrap.indent(textwrap.dedent(body).strip(), '    ')}\n",
        )
        self._write("parent.html", template)

    def parent_class(self):
        return registry.get("components.parent.Parent")

    def render_page(self):
        """The first rendering, as a page holds it."""
        return self.parent_class().render_initial({"key": "parent-1"})

    def rerender(self, known=(), state=None, action="$refresh"):
        """What the parent answers an action with."""
        return self.parent_class().update_component({"_id": "parent-1", **(state or {})}, action, [], known=known)[
            "html"
        ]


class TestIdentity(NestingTestCase):
    """The id a component written inside another is given."""

    def test_the_child_is_rendered_inside_the_parent(self):
        page = self.render_page()

        self.assertIn('<div id="child"', page)

    def test_the_child_is_told_apart_from_its_parent(self):
        page = self.render_page()

        self.assertEqual(len(set(ids_in(page))), 2)

    def test_the_id_of_the_child_is_built_from_the_one_of_its_parent(self):
        page = self.render_page()

        self.assertIn("parent-1-child-0", ids_in(page))

    def test_the_child_keeps_its_id_when_the_parent_renders_again(self):
        first = ids_in(self.render_page())
        again = ids_in(self.rerender())

        self.assertEqual(set(first) - {"parent-1"}, set(again) - {"parent-1"})

    def test_a_key_names_the_child_outright(self):
        self.write_parent('<div id="parent"><pb-child key="board" /></div>')

        self.assertIn("board", ids_in(self.render_page()))

    def test_two_children_of_the_same_kind_are_told_apart(self):
        self.write_parent('<div id="parent"><pb-child /><pb-child /></div>')

        ids = ids_in(self.render_page())

        self.assertIn("parent-1-child-0", ids)
        self.assertIn("parent-1-child-1", ids)

    def test_the_two_keep_their_ids_when_the_parent_renders_again(self):
        self.write_parent('<div id="parent"><pb-child /><pb-child /></div>')
        self.render_page()

        ids = ids_in(self.rerender())

        self.assertIn("parent-1-child-0", ids)
        self.assertIn("parent-1-child-1", ids)


class TestKeepingWhatThePageHolds(NestingTestCase):
    """A child the page already holds is left where it is."""

    def test_a_child_the_page_holds_is_not_rendered_again(self):
        self.render_page()

        answer = self.rerender(known=["parent-1-child-0"])

        self.assertIn('<div pb:id="parent-1-child-0" pb:placeholder></div>', answer)
        self.assertNotIn('id="child"', answer)

    def test_a_child_the_page_holds_is_not_handed_a_state_of_its_own(self):
        """Its state is in the page by then, and would be taken back to the defaults."""
        self.render_page()

        answer = self.rerender(known=["parent-1-child-0"])

        self.assertIsNone(snapshot_of(answer, "parent-1-child-0"))

    def test_a_child_the_page_does_not_hold_is_rendered(self):
        """One that only appears now has to arrive with everything it needs."""
        self.render_page()

        answer = self.rerender(known=[])

        self.assertIn('<div id="child"', answer)
        self.assertIsNotNone(snapshot_of(answer, "parent-1-child-0"))

    def test_the_parent_still_renders_its_own_markup(self):
        self.render_page()

        answer = self.rerender(known=["parent-1-child-0"], state={"title": "new"})

        self.assertIn("new", answer)

    def test_only_the_children_the_page_holds_are_left_out(self):
        self.write_parent('<div id="parent"><pb-child /><pb-child /></div>')
        self.render_page()

        answer = self.rerender(known=["parent-1-child-0"])

        self.assertIn('<div pb:id="parent-1-child-0" pb:placeholder></div>', answer)
        self.assertIsNotNone(snapshot_of(answer, "parent-1-child-1"))

    def test_the_first_rendering_never_leaves_a_child_out(self):
        """Nothing is on the page yet, whatever the client may have said before."""
        page = self.render_page()

        self.assertNotIn("pb:placeholder", page)
        self.assertIn('<div id="child"', page)


class TestTheChildOnItsOwn(NestingTestCase):
    """The child answers for itself, as any component does."""

    def test_the_child_carries_a_snapshot_of_its_own(self):
        page = self.render_page()

        snapshot = snapshot_of(page, "parent-1-child-0")

        self.assertEqual(snapshot["id"], "parent-1-child-0")
        self.assertTrue(snapshot["class"].endswith("Child"))

    def test_the_state_of_the_child_is_its_own(self):
        self.write_child("count = 7")

        self.assertEqual(snapshot_of(self.render_page(), "parent-1-child-0")["state"], {"count": 7})

    def test_an_action_of_the_child_leaves_the_parent_alone(self):
        self.write_child("count = 0\n\ndef bump(self):\n    self.count += 1")
        self.render_page()

        child = registry.get("components.child.Child")
        answer = child.update_component({"_id": "parent-1-child-0", "count": 4}, "bump")

        self.assertEqual(answer["snapshot"]["state"], {"count": 5})
        self.assertNotIn('id="parent"', answer["html"])
