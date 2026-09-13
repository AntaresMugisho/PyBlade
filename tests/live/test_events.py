"""Components talking to one another through events.

A component emits an event without knowing who listens; another declares what it
listens for with @on, and is called with the data the event carries. Nothing
travels directly from one to the other: the event goes out to the client with
the answer of the action that emitted it, and comes back as a request of its own
to every component that listens for it.
"""

import html
import json
import re
import unittest

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import on


def _attribute(markup, name):
    """Read back what a component wrote on its root element."""
    value = re.search(rf"pb:{name}='([^']*)'", markup).group(1)

    return json.loads(html.unescape(value))


def component(**body):
    """A live component as a developer writes one, built from the given body."""
    body.setdefault("render", lambda self: self.render_inline("<div>{{ count }}</div>", context={}))
    body.setdefault("count", 0)
    return type("Talker", (LiveComponent,), body)


class TestTheDecorator(unittest.TestCase):
    """What @on says about a method."""

    def test_a_method_declares_what_it_listens_for(self):
        cls = component(update=on("post-created")(lambda self: None))

        self.assertEqual(cls._listeners(), {"post-created": "update"})

    def test_a_method_may_listen_for_several_events(self):
        cls = component(update=on("created", "updated")(lambda self: None))

        self.assertEqual(cls._listeners(), {"created": "update", "updated": "update"})

    def test_stacked_decorators_add_up(self):
        cls = component(update=on("created")(on("updated")(lambda self: None)))

        self.assertEqual(set(cls._listeners()), {"created", "updated"})

    def test_a_method_without_the_decorator_listens_for_nothing(self):
        cls = component(update=lambda self: None)

        self.assertEqual(cls._listeners(), {})

    def test_the_decorator_leaves_the_method_callable(self):
        cls = component(update=on("created")(lambda self: "done"))

        self.assertEqual(cls("pb-test").update(), "done")

    def test_a_listener_is_still_an_action_the_client_may_call(self):
        cls = component(update=on("created")(lambda self: None))

        self.assertIn("update", cls("pb-test")._get_methods())


class TestListeningForEvents(unittest.TestCase):
    """What happens when an event comes back from the client."""

    def _emit(self, cls, event, data=None, state=None):
        return cls.update_component({"_id": "pb-test", **(state or {})}, "$event", [event, data or {}])

    def test_the_event_calls_the_method_that_listens_for_it(self):
        def update(self):
            self.count = 7

        cls = component(update=on("post-created")(update))

        result = self._emit(cls, "post-created")

        self.assertEqual(result["snapshot"]["state"]["count"], 7)

    def test_the_data_of_the_event_is_handed_to_the_method(self):
        def update(self, title):
            self.title = title

        cls = component(title="", update=on("post-created")(update))

        result = self._emit(cls, "post-created", {"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["title"], "Hello")

    def test_a_method_is_handed_only_what_it_asks_for(self):
        def update(self, title):
            self.title = title

        cls = component(title="", update=on("post-created")(update))

        result = self._emit(cls, "post-created", {"title": "Hello", "unread": 3})

        self.assertEqual(result["snapshot"]["state"]["title"], "Hello")

    def test_a_method_taking_nothing_is_called_with_nothing(self):
        cls = component(update=on("post-created")(lambda self: setattr(self, "count", 1)))

        result = self._emit(cls, "post-created", {"title": "Hello"})

        self.assertEqual(result["snapshot"]["state"]["count"], 1)

    def test_a_method_keeps_the_defaults_it_declares(self):
        def update(self, refresh=False):
            self.count = 1 if refresh else 0

        cls = component(update=on("post-created")(update))

        self.assertEqual(self._emit(cls, "post-created")["snapshot"]["state"]["count"], 0)
        self.assertEqual(self._emit(cls, "post-created", {"refresh": True})["snapshot"]["state"]["count"], 1)

    def test_a_method_taking_anything_is_handed_everything(self):
        def update(self, **data):
            self.count = len(data)

        cls = component(update=on("post-created")(update))

        result = self._emit(cls, "post-created", {"a": 1, "b": 2})

        self.assertEqual(result["snapshot"]["state"]["count"], 2)

    def test_the_component_renders_again_after_handling_an_event(self):
        cls = component(update=on("post-created")(lambda self: setattr(self, "count", 4)))

        result = self._emit(cls, "post-created")

        self.assertEqual(result["html"], '<div pb:id="pb-test">4</div>')

    def test_an_event_nobody_listens_for_is_refused(self):
        cls = component(update=on("post-created")(lambda self: None))

        with self.assertRaises(NameError):
            self._emit(cls, "post-deleted")

    def test_an_event_may_not_reach_a_method_of_the_machinery(self):
        """The name of an event is the client's to choose, the method is not."""
        cls = component()

        with self.assertRaises(NameError):
            self._emit(cls, "serialize")


class TestDynamicEventNames(unittest.TestCase):
    """An event name built from what the component holds."""

    def test_a_placeholder_is_resolved_against_the_state(self):
        cls = component(post_id=3, update=on("post-updated.{post_id}")(lambda self: None))

        self.assertEqual(cls("pb-test")._resolved_listeners(), {"post-updated.3": "update"})

    def test_a_placeholder_walks_into_what_it_names(self):
        cls = component(post={"id": 7}, update=on("post-updated.{post.id}")(lambda self: None))

        self.assertEqual(cls("pb-test")._resolved_listeners(), {"post-updated.7": "update"})

    def test_the_resolved_name_is_the_one_that_calls_the_method(self):
        cls = component(post_id=3, update=on("post-updated.{post_id}")(lambda self: setattr(self, "count", 9)))

        result = cls.update_component({"_id": "pb-test", "post_id": 3}, "$event", ["post-updated.3", {}])

        self.assertEqual(result["snapshot"]["state"]["count"], 9)

    def test_the_unresolved_name_does_not_call_the_method(self):
        cls = component(post_id=3, update=on("post-updated.{post_id}")(lambda self: None))

        with self.assertRaises(NameError):
            cls.update_component({"_id": "pb-test", "post_id": 3}, "$event", ["post-updated.{post_id}", {}])

    def test_a_placeholder_that_cannot_be_resolved_leaves_the_listener_out(self):
        cls = component(update=on("post-updated.{nowhere}")(lambda self: None))

        self.assertEqual(cls("pb-test")._resolved_listeners(), {})

    def test_a_placeholder_may_not_reach_the_machinery(self):
        cls = component(update=on("x.{_id}")(lambda self: None))

        self.assertEqual(cls("pb-test")._resolved_listeners(), {})


class TestTellingTheClient(unittest.TestCase):
    """What the client is told about the events a component listens for."""

    def test_the_snapshot_carries_the_listeners(self):
        cls = component(update=on("post-created")(lambda self: None))

        self.assertEqual(cls("pb-test").serialize()["listeners"], {"post-created": "update"})

    def test_a_component_listening_for_nothing_says_so(self):
        self.assertEqual(component()("pb-test").serialize()["listeners"], {})

    def test_the_listeners_are_signed_with_the_rest_of_the_snapshot(self):
        from pyblade.live.security import verify_snapshot

        snapshot = component(update=on("post-created")(lambda self: None))("pb-test").serialize()
        snapshot["listeners"]["post-created"] = "serialize"

        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)

    def test_the_listeners_are_not_part_of_the_state(self):
        cls = component(update=on("post-created")(lambda self: None))

        self.assertNotIn("listeners", cls("pb-test")._get_state())


class TestScopingAnEvent(unittest.TestCase):
    """Who an emitted event is meant for."""

    def _emitted(self, action):
        return component(go=action).update_component({"_id": "pb-test"}, "go")["events"][0]

    def test_an_event_is_for_everyone_by_default(self):
        event = self._emitted(lambda self: self.emit("saved"))

        self.assertEqual(event, {"name": "saved", "data": {}})

    def test_to_names_the_component_the_event_is_for(self):
        event = self._emitted(lambda self: self.emit("saved").to("Dashboard"))

        self.assertEqual(event["to"], "Dashboard")

    def test_self_keeps_the_event_for_the_component_that_emitted_it(self):
        event = self._emitted(lambda self: self.emit("saved").self())

        self.assertIs(event["self"], True)

    def test_the_data_survives_the_modifiers(self):
        event = self._emitted(lambda self: self.emit("saved", id=3).to("Dashboard"))

        self.assertEqual(event["data"], {"id": 3})

    def test_dispatch_may_be_scoped_too(self):
        event = self._emitted(lambda self: self.dispatch("saved").self())

        self.assertIs(event["self"], True)

    def test_the_modifiers_may_be_chained(self):
        event = self._emitted(lambda self: self.emit("saved").to("Dashboard").self())

        self.assertEqual((event["to"], event["self"]), ("Dashboard", True))


class TestEventsOnTheFirstRendering(unittest.TestCase):
    """An event emitted before the page is even on screen."""

    def test_an_event_emitted_while_mounting_reaches_the_client(self):
        cls = component(mount=lambda self: self.emit("ready", id=1))

        rendered = cls.render_initial({"key": "pb-test"})

        self.assertEqual(_attribute(rendered, "events"), [{"name": "ready", "data": {"id": 1}}])

    def test_the_events_are_written_apart_from_the_snapshot(self):
        """The snapshot travels back to the server; the events only go out."""
        cls = component(mount=lambda self: self.emit("ready"))

        rendered = cls.render_initial({"key": "pb-test"})

        self.assertEqual(
            set(_attribute(rendered, "snapshot")),
            {"id", "class", "state", "listeners", "confirmations", "errors", "checksum"},
        )

    def test_a_component_emitting_nothing_writes_no_events(self):
        rendered = component().render_initial({"key": "pb-test"})

        self.assertNotIn("pb:events", rendered)
