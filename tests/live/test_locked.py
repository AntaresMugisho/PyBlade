"""Properties the page may read but never write.

What a snapshot holds is signed, so the page cannot change it. What the page
sends along with a request is not: the fields it has typed into, and `$set`. A
property that is a reference to something -- the post being edited, the owner of
it -- must not be rewritten from there, and is locked against it.
"""

import unittest

from pyblade.live import LiveComponent, lock
from pyblade.live.testing import live


@lock("post_id", "owner_id")
class Editor(LiveComponent):
    post_id: int
    owner_id = 2
    title = ""

    def mount(self):
        self.post_id = 1

    def reassign(self, post_id):
        self.post_id = post_id

    def render(self):
        return self.render_inline("<div>{{ post_id }}:{{ title }}</div>")


STATE = {"_id": "pb-test", "post_id": 1, "owner_id": 2, "title": ""}


def update(component, action, params=(), updates=None):
    return component.update_component(dict(STATE), action, list(params), updates=updates)


class TestRefusingThePage(unittest.TestCase):
    def test_a_locked_property_is_refused_by_set(self):
        with self.assertRaises(PermissionError):
            update(Editor, "$set", ["post_id", 9])

    def test_a_locked_property_is_refused_among_the_updates(self):
        with self.assertRaises(PermissionError):
            update(Editor, "$refresh", updates={"owner_id": 9})

    def test_the_refusal_says_why(self):
        with self.assertRaisesRegex(PermissionError, "post_id.*locked"):
            update(Editor, "$set", ["post_id", 9])

    def test_one_locked_among_the_updates_leaves_the_others_unset(self):
        seen = []

        @lock("post_id")
        class Watched(Editor):
            def updating(self, name, value):
                seen.append(name)

        with self.assertRaises(PermissionError):
            update(Watched, "$refresh", updates={"title": "Typed", "post_id": 9})

        self.assertEqual(seen, [])

    def test_a_dotted_name_is_locked_by_its_first_part(self):
        with self.assertRaisesRegex(PermissionError, "locked"):
            Editor("pb-test")._check_settable_from_client("post_id.value")

    def test_a_property_that_was_not_locked_is_still_set(self):
        state = update(Editor, "$set", ["title", "Hi"])["snapshot"]["state"]

        self.assertEqual(state["title"], "Hi")


class TestWhatIsStillAllowed(unittest.TestCase):
    def test_the_component_may_change_it_itself(self):
        editor = live(Editor)

        editor.call("reassign", 5)

        self.assertEqual(editor.state["post_id"], 5)

    def test_it_is_set_while_mounting(self):
        self.assertEqual(live(Editor).state["post_id"], 1)

    def test_the_page_still_reads_it(self):
        live(Editor).assert_sees("1:")

    def test_it_still_travels_in_the_snapshot(self):
        # A lock is not a secret: what must not be seen belongs in a private name
        self.assertIn("post_id", live(Editor).state)

    def test_the_test_helper_is_refused_like_the_page(self):
        with self.assertRaises(PermissionError):
            live(Editor).set("post_id", 9)


class TestInheritingLocks(unittest.TestCase):
    def test_a_subclass_keeps_the_locks_of_its_parent(self):
        class Child(Editor):
            note = ""

        with self.assertRaises(PermissionError):
            update(Child, "$set", ["post_id", 9])

    def test_a_subclass_may_lock_more(self):
        @lock("note")
        class Child(Editor):
            note = ""

        with self.assertRaises(PermissionError):
            update(Child, "$set", ["note", "x"])
        with self.assertRaises(PermissionError):
            update(Child, "$set", ["post_id", 9])

    def test_a_subclass_does_not_lock_its_parent(self):
        @lock("note")
        class Child(Editor):
            note = ""

        self.assertEqual(Editor._locked_names(), {"post_id", "owner_id"})
        self.assertEqual(Child._locked_names(), {"post_id", "owner_id", "note"})


class TestWritingTheLock(unittest.TestCase):
    def test_a_name_the_component_does_not_declare_is_refused_at_once(self):
        # A typo would leave the property open, and nothing would say so
        with self.assertRaisesRegex(AttributeError, "post_idd"):

            @lock("post_idd")
            class Typo(LiveComponent):
                post_id = 1

    def test_a_property_declared_by_its_type_alone_counts(self):
        @lock("post_id")
        class Declared(LiveComponent):
            post_id: int

        self.assertEqual(Declared._locked_names(), {"post_id"})

    def test_a_property_inherited_from_a_parent_counts(self):
        @lock("title")
        class Child(Editor):
            pass

        self.assertIn("title", Child._locked_names())

    def test_the_decorator_hands_back_the_class(self):
        @lock("title")
        class Same(LiveComponent):
            title = ""

        self.assertTrue(issubclass(Same, LiveComponent))

    def test_the_locks_are_not_state(self):
        self.assertNotIn("_locked", live(Editor).state)


if __name__ == "__main__":
    unittest.main()
