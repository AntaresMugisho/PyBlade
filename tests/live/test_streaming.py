"""Sending content to the page while an action is still running.

An action that takes a while -- writing an answer a word at a time, working
through a long list -- has something to show before it has finished. It streams
that to an element on the page, and the page shows it as it arrives rather than
all at once when the action returns.
"""

import json
import unittest

from django.test import override_settings

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import streamed


def component(**body):
    body.setdefault("render", lambda self: self.render_inline("<div>{{ done }}</div>", context={}))
    body.setdefault("done", False)
    return type("Writer", (LiveComponent,), body)


class TestSayingWhichActionsStream(unittest.TestCase):
    """@streamed is what asks for a response that arrives in pieces."""

    def test_an_action_says_it_streams(self):
        cls = component(write=streamed(lambda self: None))

        self.assertTrue(cls._streams_from("write"))

    def test_an_action_that_does_not_say_so(self):
        cls = component(write=lambda self: None)

        self.assertFalse(cls._streams_from("write"))

    def test_a_name_that_is_not_an_action_of_its_own(self):
        cls = component(write=streamed(lambda self: None))

        self.assertFalse(cls._streams_from("$refresh"))
        self.assertFalse(cls._streams_from("serialize"))
        self.assertFalse(cls._streams_from("nowhere"))

    def test_the_decorator_leaves_the_action_callable(self):
        cls = component(write=streamed(lambda self: "done"))

        self.assertEqual(cls("pb-test").write(), "done")


class TestStreamingWithNowhereToStreamTo(unittest.TestCase):
    """An action that streams without asking for a streamed response."""

    def test_what_it_streams_still_reaches_the_client(self):
        def write(self):
            self.stream("summary", "Hello ")
            self.stream("summary", "world")

        result = component(write=write).update_component({"_id": "pb-test"}, "write")

        self.assertEqual(
            result["streams"],
            [
                {"to": "summary", "content": "Hello ", "replace": False},
                {"to": "summary", "content": "world", "replace": False},
            ],
        )

    def test_an_action_streaming_nothing_says_nothing(self):
        result = component(write=lambda self: None).update_component({"_id": "pb-test"}, "write")

        self.assertNotIn("streams", result)

    def test_replacing_rather_than_adding_to_what_is_there(self):
        def write(self):
            self.stream("summary", "All of it", replace=True)

        result = component(write=write).update_component({"_id": "pb-test"}, "write")

        self.assertIs(result["streams"][0]["replace"], True)

    def test_what_is_streamed_is_not_part_of_the_state(self):
        def write(self):
            self.stream("summary", "Hello")

        cls = component(write=write)
        result = cls.update_component({"_id": "pb-test"}, "write")

        self.assertNotIn("streams", result["snapshot"]["state"])
        self.assertNotIn("_streams", result["snapshot"]["state"])


class TestStreamingAsItHappens(unittest.TestCase):
    """The response that arrives in pieces, a line of JSON at a time."""

    def _lines(self, cls, action="write", **kwargs):
        from pyblade.live.views import streamed_response

        return [json.loads(line) for line in streamed_response(cls, {"_id": "pb-test"}, action, **kwargs)]

    def test_every_piece_arrives_before_the_answer(self):
        def write(self):
            self.stream("summary", "one")
            self.stream("summary", "two")
            self.done = True

        lines = self._lines(component(write=streamed(write)))

        self.assertEqual(
            [line["stream"]["content"] for line in lines if "stream" in line],
            ["one", "two"],
        )

    def test_the_answer_comes_last(self):
        def write(self):
            self.stream("summary", "one")
            self.done = True

        lines = self._lines(component(write=streamed(write)))

        self.assertIn("stream", lines[0])
        self.assertIn("snapshot", lines[-1])
        self.assertIs(lines[-1]["snapshot"]["state"]["done"], True)

    def test_the_new_markup_comes_with_the_answer(self):
        lines = self._lines(component(write=streamed(lambda self: None)))

        self.assertIn('<div pb:id="pb-test">', lines[-1]["html"])

    def test_an_action_that_fails_says_so_rather_than_stopping_short(self):
        def write(self):
            self.stream("summary", "one")
            raise ValueError("no good")

        lines = self._lines(component(write=streamed(write)))

        self.assertEqual(lines[0]["stream"]["content"], "one")
        self.assertIn("no good", lines[-1]["error"])

    def test_in_production_what_went_wrong_stays_on_the_server(self):
        def write(self):
            raise ValueError("password=hunter2")

        with (
            override_settings(DEBUG=False),
            self.assertLogs("pyblade.live", level="ERROR") as logged,
        ):
            lines = self._lines(component(write=streamed(write)))

        self.assertNotIn("hunter2", json.dumps(lines[-1]))
        self.assertEqual(lines[-1], {"error": "Something went wrong on the server."})
        self.assertIn("hunter2", "\n".join(logged.output))

    def test_in_production_a_refusal_still_says_why(self):
        def write(self):
            raise PermissionError("You can't do that.")

        with override_settings(DEBUG=False):
            lines = self._lines(component(write=streamed(write)))

        self.assertEqual(lines[-1], {"error": "You can't do that."})

    def test_the_pieces_keep_the_order_they_were_streamed_in(self):
        def write(self):
            for number in range(20):
                self.stream("counter", str(number))

        lines = self._lines(component(write=streamed(write)))
        streamed_content = [line["stream"]["content"] for line in lines if "stream" in line]

        self.assertEqual(streamed_content, [str(number) for number in range(20)])

    def test_each_piece_is_a_line_of_its_own(self):
        from pyblade.live.views import streamed_response

        def write(self):
            self.stream("summary", "one")

        lines = list(streamed_response(component(write=streamed(write)), {"_id": "pb-test"}, "write"))

        self.assertTrue(all(line.endswith("\n") for line in lines))
        self.assertTrue(all(line.count("\n") == 1 for line in lines))
