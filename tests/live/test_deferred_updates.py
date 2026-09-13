"""What a form holds before it is sent.

A field written pb:model keeps what is typed into it on the page and says
nothing until the component next has something to ask the server. What it holds
by then travels with that request, so the action runs against the form as the
reader left it rather than as the server last saw it.
"""

import unittest

from pyblade.live.base import LiveComponent


def component(**body):
    """A live component as a developer writes one, built from the given body."""
    body.setdefault("render", lambda self: self.render_inline("<div>{{ title }}</div>", context={}))
    body.setdefault("title", "")
    return type("Form", (LiveComponent,), body)


def send(cls, action="$refresh", args=None, updates=None, state=None):
    return cls.update_component(
        {"_id": "pb-test", **(state or {})},
        action,
        args or [],
        updates=updates,
    )


class TestApplyingWhatWasTyped(unittest.TestCase):
    def test_what_was_typed_reaches_the_component(self):
        result = send(component(), updates={"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["title"], "Hello")

    def test_several_fields_travel_together(self):
        cls = component(title="", body="")

        result = send(cls, updates={"title": "Hello", "body": "World"})

        self.assertEqual(result["snapshot"]["state"], {"title": "Hello", "body": "World"})

    def test_the_action_runs_against_what_was_typed(self):
        """The point of it: save() sees the form as the reader left it."""

        def save(self):
            self.saved = self.title

        cls = component(saved="", save=save)

        result = send(cls, action="save", updates={"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["saved"], "Hello")

    def test_nothing_typed_changes_nothing(self):
        result = send(component(), state={"title": "Unchanged"})

        self.assertEqual(result["snapshot"]["state"]["title"], "Unchanged")

    def test_what_is_not_a_map_of_fields_is_ignored(self):
        result = send(component(), updates=["title", "Hello"], state={"title": "Unchanged"})

        self.assertEqual(result["snapshot"]["state"]["title"], "Unchanged")


class TestTheHooksItRuns(unittest.TestCase):
    """A field arriving this way is set the way any property is."""

    def test_the_general_hooks_run(self):
        def updated(self, prop, value):
            self.seen.append((prop, value))

        cls = component(seen=[], updated=updated)

        result = send(cls, updates={"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["seen"], [("title", "Hello")])

    def test_the_hook_named_after_the_property_runs(self):
        def updated_title(self, value):
            self.slug = value.lower()

        cls = component(slug="", updated_title=updated_title)

        result = send(cls, updates={"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["slug"], "hello")

    def test_a_hook_may_refuse_what_was_typed(self):
        def updating_title(self, value):
            if len(value) > 5:
                raise ValueError("too long")

        cls = component(updating_title=updating_title)

        with self.assertRaises(ValueError):
            send(cls, updates={"title": "far too long"})


class TestWhatTheClientMayNotSet(unittest.TestCase):
    """The names of the fields come from the page, so they are not to be trusted."""

    def test_the_machinery_is_out_of_reach(self):
        with self.assertRaises(AttributeError):
            send(component(), updates={"template_name": "anything"})

    def test_a_private_name_is_out_of_reach(self):
        with self.assertRaises(AttributeError):
            send(component(), updates={"_id": "somewhere-else"})


class TestAlongsideTheOtherActions(unittest.TestCase):
    def test_a_property_set_on_its_own_still_works(self):
        result = send(component(), action="$set", args=["title", "Typed"])

        self.assertEqual(result["snapshot"]["state"]["title"], "Typed")

    def test_what_was_typed_is_applied_before_the_action_is_called(self):
        def save(self):
            self.order.append(self.title)

        cls = component(order=[], save=save, updating=lambda self, p, v: self.order.append("updating"))

        result = send(cls, action="save", updates={"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["order"], ["updating", "Hello"])
