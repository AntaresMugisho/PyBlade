"""Testing a live component without a browser and without a server.

What a developer writing components needs is to drive one the way a page does --
set a property, call an action, hand it an event -- and then ask what it holds
and what it shows. That is what `live()` is: the endpoint's own seam, with the
state round-tripped through JSON at every step so that a property which could
never travel fails here rather than in somebody's browser.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import lazy, on, renderless, validate
from pyblade.live.testing import live
from pyblade.live.uploads import TemporaryUpload


class Counter(LiveComponent):
    count = 0
    note = ""

    def mount(self, start=0):
        self.count = start

    def increment(self, by=1):
        self.count += by

    def render(self):
        return self.render_inline("<div>Count: {{ count }} {{ note }}</div>", context={})


class Post(LiveComponent):
    title = ""
    saved = False

    rules = {"title": forms.CharField(max_length=10)}

    @validate
    def save(self):
        self.saved = True

    def leave(self):
        return self.redirect("/posts")

    @renderless
    def touch(self):
        self.title = self.title.upper()

    @on("post-created")
    def welcome(self, name=""):
        self.title = f"Welcome {name}"

    def shout(self):
        self.emit("shouted", what=self.title)

    def render(self):
        return self.render_inline("<div>Post: {{ title }}</div>", context={})


class TestDrivingAComponent(unittest.TestCase):
    def test_it_is_mounted_and_rendered(self):
        counter = live(Counter)

        self.assertEqual(counter.state["count"], 0)
        self.assertIn("Count: 0", counter.html)

    def test_what_it_is_given_reaches_mount(self):
        self.assertEqual(live(Counter, start=5).state["count"], 5)

    def test_a_property_may_be_set_as_a_field_sets_one(self):
        counter = live(Counter).set("note", "hello")

        self.assertEqual(counter.state["note"], "hello")
        self.assertIn("hello", counter.html)

    def test_an_action_may_be_called(self):
        self.assertEqual(live(Counter).call("increment").state["count"], 1)

    def test_with_the_arguments_it_takes(self):
        self.assertEqual(live(Counter).call("increment", 4).state["count"], 4)

    def test_one_step_carries_on_from_the_last(self):
        counter = live(Counter).call("increment").call("increment").set("note", "twice")

        self.assertEqual(counter.state["count"], 2)
        self.assertIn("Count: 2 twice", counter.html)

    def test_it_may_be_handed_an_event_as_another_component_would(self):
        post = live(Post).emit("post-created", name="Antares")

        self.assertEqual(post.state["title"], "Welcome Antares")

    def test_it_may_simply_be_rendered_again(self):
        self.assertIn("Count: 0", live(Counter).refresh().html)

    def test_what_it_emitted_is_there_to_read(self):
        post = live(Post).set("title", "Hi").call("shout")

        self.assertEqual(post.emitted[0]["name"], "shouted")
        self.assertEqual(post.emitted[0]["data"], {"what": "Hi"})

    def test_an_action_that_renders_nothing_leaves_the_markup_alone(self):
        post = live(Post).set("title", "Hi").call("touch")

        self.assertEqual(post.state["title"], "HI")
        self.assertIn("Post: Hi", post.html)


class TestWhatItSays(unittest.TestCase):
    def test_it_can_be_asked_what_it_shows(self):
        counter = live(Counter, start=3)

        self.assertTrue(counter.sees("Count: 3"))
        self.assertFalse(counter.sees("Count: 4"))

    def test_saying_it_shows_something_it_does_not_fails_the_test(self):
        with self.assertRaises(AssertionError) as caught:
            live(Counter).assert_sees("Count: 9")

        self.assertIn("Count: 9", str(caught.exception))
        self.assertIn("Count: 0", str(caught.exception))

    def test_saying_it_does_not_show_something_it_does_fails_the_test(self):
        with self.assertRaises(AssertionError):
            live(Counter).assert_does_not_see("Count: 0")

    def test_what_is_shown_is_the_markup_and_not_the_state_that_rides_with_it(self):
        """A snapshot in the markup would make every assertion nearly true."""
        self.assertNotIn("pb:snapshot", live(Counter).html)


class TestCheckingWhatItHolds(unittest.TestCase):
    def test_what_was_wrong_is_there_to_read(self):
        post = live(Post).set("title", "far too long a title").call("save")

        self.assertIn("title", post.errors)

    def test_an_action_that_did_not_hold_up_did_not_run(self):
        post = live(Post).set("title", "far too long a title").call("save")

        self.assertFalse(post.state["saved"])

    def test_it_may_be_asked_to_be_wrong(self):
        live(Post).set("title", "far too long a title").call("save").assert_invalid("title")

    def test_being_right_when_it_should_be_wrong_fails_the_test(self):
        with self.assertRaises(AssertionError):
            live(Post).set("title", "fine").call("save").assert_invalid("title")

    def test_it_may_be_asked_to_be_right(self):
        live(Post).set("title", "fine").call("save").assert_valid()

    def test_being_wrong_when_it_should_be_right_fails_the_test(self):
        with self.assertRaises(AssertionError) as caught:
            live(Post).set("title", "far too long a title").call("save").assert_valid()

        self.assertIn("title", str(caught.exception))


class TestGoingSomewhereElse(unittest.TestCase):
    def test_where_it_sent_the_reader_is_there_to_read(self):
        self.assertEqual(live(Post).call("leave").redirected_to, "/posts")

    def test_it_may_be_asked_where_it_sent_them(self):
        live(Post).call("leave").assert_redirected_to("/posts")

    def test_being_sent_somewhere_else_fails_the_test(self):
        with self.assertRaises(AssertionError) as caught:
            live(Post).call("leave").assert_redirected_to("/elsewhere")

        self.assertIn("/posts", str(caught.exception))

    def test_going_nowhere_is_going_nowhere(self):
        self.assertIsNone(live(Post).redirected_to)


@lazy(lines=2)
class Dashboard(LiveComponent):
    figures = ""

    def mount(self, month="September"):
        self.figures = f"{month}: 12,480 readers"

    def render(self):
        return self.render_inline("<div>{{ figures }}</div>", context={})


class TestALazyComponent(unittest.TestCase):
    def test_it_is_loaded_unless_the_test_asks_otherwise(self):
        self.assertIn("12,480 readers", live(Dashboard).html)

    def test_what_it_was_given_still_reaches_mount(self):
        self.assertIn("August", live(Dashboard, month="August").html)

    def test_the_skeleton_may_be_looked_at_instead(self):
        dashboard = live(Dashboard, load=False)

        self.assertIn("pb-skeleton", dashboard.html)
        self.assertNotIn("12,480", dashboard.html)

    def test_and_loaded_when_the_test_is_ready(self):
        dashboard = live(Dashboard, load=False).load()

        self.assertIn("12,480 readers", dashboard.html)


class Gallery(LiveComponent):
    photo = None
    kept = ""

    def keep(self):
        self.kept = self.photo.name

    def render(self):
        return self.render_inline("<div>{{ kept }}</div>", context={})


class TestAFileOnItsWay(unittest.TestCase):
    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.override = override_settings(MEDIA_ROOT=str(self.media), MEDIA_URL="/media/")
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def test_a_file_may_be_uploaded_as_a_reader_would(self):
        gallery = live(Gallery).upload("photo", SimpleUploadedFile("holiday.png", b"a picture"))

        self.assertTrue(gallery.state["photo"].startswith("pyblade-upload:"))

    def test_and_the_action_is_handed_the_file(self):
        gallery = live(Gallery).upload("photo", SimpleUploadedFile("holiday.png", b"a picture")).call("keep")

        self.assertEqual(gallery.state["kept"], "holiday.png")

    def test_several_files_may_be_uploaded_at_once(self):
        gallery = live(Gallery).upload(
            "photo",
            [
                SimpleUploadedFile("one.png", b"a"),
                SimpleUploadedFile("two.png", b"b"),
            ],
        )

        self.assertEqual(len(gallery.state["photo"]), 2)

    def test_the_component_holds_the_file_itself(self):
        gallery = live(Gallery).upload("photo", SimpleUploadedFile("holiday.png", b"a picture"))

        self.assertIsInstance(gallery.component.photo, TemporaryUpload)


class Hoarder(LiveComponent):
    kept = ""

    def keep_something_impossible(self):
        self.kept = object()

    def render(self):
        return self.render_inline("<div>x</div>", context={})


class TestSomethingThatCouldNeverTravel(unittest.TestCase):
    def test_a_property_a_snapshot_cannot_carry_fails_the_test_here(self):
        with self.assertRaises(TypeError) as caught:
            live(Hoarder).call("keep_something_impossible")

        self.assertIn("Hoarder", str(caught.exception))
        self.assertIn("kept", str(caught.exception))


class TestWhatItEmitted(unittest.TestCase):
    def test_it_may_be_asked_what_it_emitted(self):
        live(Post).set("title", "Hi").call("shout").assert_emitted("shouted")

    def test_emitting_nothing_of_the_sort_fails_the_test(self):
        with self.assertRaises(AssertionError) as caught:
            live(Post).set("title", "Hi").call("shout").assert_emitted("saved")

        self.assertIn("shouted", str(caught.exception))
