"""What the page may set on a component: the properties it holds, and nothing else.

`$set` and the fields written pb:model come from the page, which anyone can
write to. A name the component does not hold as a property -- one of its
methods above all, which setting would shadow for the rest of the request --
is refused before any hook runs.
"""

import unittest

from pyblade.live.base import LiveComponent


class Post(LiveComponent):
    title = ""
    draft: bool  # declared, with no value yet

    def mount(self):
        self.slug = "hello"  # set while the component is alive

    def can_edit(self):
        return False

    @property
    def summary(self):
        return self.title[:10]

    def save(self):
        if self.can_edit():
            self.saved = True

    def render(self):
        return self.render_inline("<div>{{ title }}</div>", context={})


STATE = {"_id": "pb-test", "title": "", "slug": "hello"}


def update(action, params=(), updates=None):
    return Post.update_component(dict(STATE), action, list(params), updates=updates)


class TestSet(unittest.TestCase):
    def test_a_declared_property_is_set(self):
        self.assertEqual(update("$set", ["title", "Hi"])["snapshot"]["state"]["title"], "Hi")

    def test_one_set_while_the_component_was_alive_is_set(self):
        self.assertEqual(update("$set", ["slug", "bye"])["snapshot"]["state"]["slug"], "bye")

    def test_one_declared_without_a_value_is_set(self):
        self.assertIs(update("$set", ["draft", True])["snapshot"]["state"]["draft"], True)

    def test_a_method_is_refused(self):
        with self.assertRaises(PermissionError):
            update("$set", ["can_edit", True])

    def test_a_name_the_component_does_not_hold_is_refused(self):
        with self.assertRaises(PermissionError):
            update("$set", ["is_admin", True])

    def test_a_computed_property_is_refused(self):
        with self.assertRaises(PermissionError):
            update("$set", ["summary", "x"])


class TestUpdates(unittest.TestCase):
    """What pb:model fields send along with any request."""

    def test_the_properties_it_holds_are_set(self):
        state = update("$refresh", updates={"title": "Typed"})["snapshot"]["state"]

        self.assertEqual(state["title"], "Typed")

    def test_a_method_among_them_is_refused_and_nothing_is_set(self):
        seen = []

        class Watched(Post):
            def updating(self, name, value):
                seen.append(name)

        with self.assertRaises(PermissionError):
            Watched.update_component(dict(STATE), "save", [], updates={"title": "x", "can_edit": True})

        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
