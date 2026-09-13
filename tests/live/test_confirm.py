"""An action that has to be confirmed before it runs.

A destructive action is written @confirm, and the page asks before calling it.
The mark is on the action rather than on the button, so that an action reached
by a button that forgot to ask, or by a call written by hand, is refused rather
than carried out. It is a guard against reaching the action by accident, not a
wall against a client that means harm: whoever can call the action at all can
say they confirmed it.
"""

import unittest

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import confirm


def component(**body):
    body.setdefault("render", lambda self: self.render_inline("<div>{{ posts }}</div>", context={}))
    body.setdefault("posts", 2)
    return type("Posts", (LiveComponent,), body)


def call(cls, action="delete", confirmed=False, args=None):
    return cls.update_component({"_id": "pb-test"}, action, args or [], confirmed=confirmed)


class TestTheDecorator(unittest.TestCase):
    """What @confirm says about an action."""

    def test_an_action_says_it_must_be_confirmed(self):
        cls = component(delete=confirm("Delete this post?")(lambda self: None))

        self.assertEqual(cls._confirmations(), {"delete": "Delete this post?"})

    def test_it_may_be_written_without_a_message(self):
        cls = component(delete=confirm(lambda self: None))

        self.assertIn("delete", cls._confirmations())

    def test_an_action_that_is_not_marked_says_nothing(self):
        cls = component(delete=lambda self: None)

        self.assertEqual(cls._confirmations(), {})

    def test_the_decorator_leaves_the_action_callable(self):
        cls = component(delete=confirm("Sure?")(lambda self: "done"))

        self.assertEqual(cls("pb-test").delete(), "done")

    def test_the_message_reaches_the_client(self):
        cls = component(delete=confirm("Delete this post?")(lambda self: None))

        self.assertEqual(
            cls("pb-test").serialize()["confirmations"], {"delete": "Delete this post?"}
        )

    def test_what_it_says_is_signed_with_the_rest_of_the_snapshot(self):
        from pyblade.live.security import verify_snapshot

        snapshot = component(delete=confirm("Sure?")(lambda self: None))("pb-test").serialize()
        snapshot["confirmations"]["delete"] = "Go right ahead"

        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)


class TestRefusingWhatWasNotConfirmed(unittest.TestCase):
    def test_an_action_that_was_not_confirmed_is_refused(self):
        cls = component(delete=confirm("Sure?")(lambda self: setattr(self, "posts", 0)))

        with self.assertRaises(PermissionError):
            call(cls)

    def test_the_action_does_not_run(self):
        cls = component(delete=confirm("Sure?")(lambda self: setattr(self, "posts", 0)))

        with self.assertRaises(PermissionError):
            call(cls)

        self.assertEqual(cls("pb-test").posts, 2)

    def test_an_action_that_was_confirmed_runs(self):
        cls = component(delete=confirm("Sure?")(lambda self: setattr(self, "posts", 0)))

        result = call(cls, confirmed=True)

        self.assertEqual(result["snapshot"]["state"]["posts"], 0)

    def test_an_action_that_asks_nothing_runs_either_way(self):
        cls = component(delete=lambda self: setattr(self, "posts", 0))

        self.assertEqual(call(cls)["snapshot"]["state"]["posts"], 0)

    def test_what_the_error_says_names_the_action(self):
        cls = component(delete=confirm("Sure?")(lambda self: None))

        with self.assertRaises(PermissionError) as raised:
            call(cls)

        self.assertIn("delete", str(raised.exception))


class TestAlongsideTheOtherActions(unittest.TestCase):
    def test_an_event_may_reach_an_action_that_must_be_confirmed(self):
        from pyblade.live.decorators import on

        cls = component(delete=on("wipe")(confirm("Sure?")(lambda self: setattr(self, "posts", 0))))

        with self.assertRaises(PermissionError):
            cls.update_component({"_id": "pb-test"}, "$event", ["wipe", {}])

        result = cls.update_component({"_id": "pb-test"}, "$event", ["wipe", {}], confirmed=True)
        self.assertEqual(result["snapshot"]["state"]["posts"], 0)

    def test_setting_a_property_is_not_an_action_to_confirm(self):
        cls = component(delete=confirm("Sure?")(lambda self: None))

        result = cls.update_component({"_id": "pb-test"}, "$set", ["posts", 5])

        self.assertEqual(result["snapshot"]["state"]["posts"], 5)

    def test_what_must_be_confirmed_is_not_part_of_the_state(self):
        cls = component(delete=confirm("Sure?")(lambda self: None))

        self.assertNotIn("confirmations", cls("pb-test")._get_state())
