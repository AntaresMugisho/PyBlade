"""A file on its way from the page to wherever it is going to be kept.

Choosing a file does not wait for an action: it is sent on its own, checked, and
put somewhere temporary, and the property is left holding a signed note saying
where. The action that runs later is handed the file and decides where it
belongs. That is what lets a file be uploaded while the rest of the form is
still being filled in, and what makes progress and cancelling mean anything.
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from pyblade.live.base import LiveComponent
from django.core.files.storage import default_storage

from pyblade.live import uploads as uploads_module
from pyblade.live.uploads import (
    MAX_AGE,
    MaxFileSize,
    MultipleFileField,
    TemporaryUpload,
    is_upload_reference,
    store_temporarily,
    sweep_if_due,
    sweep_temporary_uploads,
)


def a_file(name="note.txt", content=b"hello", content_type="text/plain"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class UploadTestCase(unittest.TestCase):
    """A place for the temporary files to go, thrown away afterwards."""

    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.override = override_settings(MEDIA_ROOT=str(self.media), MEDIA_URL="/media/")
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)


class TestRefusingWhatIsTooBig(unittest.TestCase):
    """The one thing Django has no field for, so PyBlade brings it."""

    def test_a_size_may_be_written_the_way_people_write_sizes(self):
        self.assertEqual(MaxFileSize("500kb").max_bytes, 500 * 1024)
        self.assertEqual(MaxFileSize("2mb").max_bytes, 2 * 1024 * 1024)
        self.assertEqual(MaxFileSize("1gb").max_bytes, 1024 ** 3)

    def test_a_number_of_bytes_may_be_given_outright(self):
        self.assertEqual(MaxFileSize(4096).max_bytes, 4096)

    def test_a_size_it_cannot_read_is_refused_at_once(self):
        with self.assertRaises(ValueError):
            MaxFileSize("a few megabytes")

    def test_a_file_within_the_size_passes(self):
        MaxFileSize("1kb")(a_file(content=b"x" * 100))

    def test_a_file_over_it_does_not(self):
        with self.assertRaises(ValidationError):
            MaxFileSize("1kb")(a_file(content=b"x" * 2000))

    def test_what_it_says_names_the_size_that_was_allowed(self):
        with self.assertRaises(ValidationError) as raised:
            MaxFileSize("1kb")(a_file(content=b"x" * 2000))

        self.assertIn("1kb", str(raised.exception))


class TestPuttingAFileSomewhereTemporary(UploadTestCase):
    def test_the_file_is_kept(self):
        upload = store_temporarily(a_file(content=b"the contents"))

        self.assertEqual(upload.open().read(), b"the contents")

    def test_what_it_was_called_is_remembered(self):
        upload = store_temporarily(a_file(name="holiday.txt"))

        self.assertEqual(upload.name, "holiday.txt")

    def test_how_big_it_is_and_what_it_holds_are_too(self):
        upload = store_temporarily(a_file(content=b"12345", content_type="text/plain"))

        self.assertEqual(upload.size, 5)
        self.assertEqual(upload.content_type, "text/plain")

    def test_two_files_of_the_same_name_do_not_become_one(self):
        first = store_temporarily(a_file(name="same.txt", content=b"first"))
        second = store_temporarily(a_file(name="same.txt", content=b"second"))

        self.assertNotEqual(first.stored_name, second.stored_name)
        self.assertEqual(first.open().read(), b"first")

    def test_what_the_page_is_given_says_nothing_of_where_the_file_is(self):
        """The page is handed a note it cannot read, only hand back."""
        upload = store_temporarily(a_file(name="holiday.txt"))

        self.assertNotIn(str(self.media), upload.reference)
        self.assertNotIn("pyblade-tmp", upload.reference)


class TestTheNoteThePageHandsBack(UploadTestCase):
    def test_a_note_is_recognised_for_what_it_is(self):
        upload = store_temporarily(a_file())

        self.assertTrue(is_upload_reference(upload.reference))
        self.assertFalse(is_upload_reference("just some text"))
        self.assertFalse(is_upload_reference(None))
        self.assertFalse(is_upload_reference(42))

    def test_the_file_is_found_again_from_it(self):
        upload = store_temporarily(a_file(name="holiday.txt", content=b"sun"))

        again = TemporaryUpload.from_reference(upload.reference)

        self.assertEqual(again.name, "holiday.txt")
        self.assertEqual(again.open().read(), b"sun")

    def test_a_note_that_was_written_over_is_worth_nothing(self):
        upload = store_temporarily(a_file())
        tampered = upload.reference[:-4] + "aaaa"

        self.assertIsNone(TemporaryUpload.from_reference(tampered))

    def test_a_note_made_up_out_of_nothing_is_worth_nothing(self):
        self.assertIsNone(TemporaryUpload.from_reference("pyblade-upload:not-a-real-note"))

    def test_a_note_too_old_to_trust_is_worth_nothing(self):
        upload = store_temporarily(a_file())

        self.assertIsNone(TemporaryUpload.from_reference(upload.reference, max_age=-1))


class TestKeepingTheFileForGood(UploadTestCase):
    def test_the_file_is_moved_where_it_was_asked_for(self):
        upload = store_temporarily(a_file(name="holiday.txt", content=b"sun"))

        path = upload.store("photos")

        self.assertTrue(path.startswith("photos/"))
        self.assertEqual((self.media / path).read_bytes(), b"sun")

    def test_it_keeps_the_name_it_came_with(self):
        upload = store_temporarily(a_file(name="holiday.txt"))

        self.assertTrue(upload.store("photos").endswith("holiday.txt"))

    def test_it_may_be_given_another(self):
        upload = store_temporarily(a_file(name="holiday.txt"))

        self.assertEqual(upload.store("photos", name="summer.txt"), "photos/summer.txt")

    def test_the_temporary_one_is_not_left_behind(self):
        upload = store_temporarily(a_file())
        temporary = self.media / upload.stored_name

        upload.store("photos")

        self.assertFalse(temporary.exists())


class TestAFilePropertyOfAComponent(UploadTestCase):
    """What a component holds, and what travels to the page and back."""

    def _component(self, **body):
        body.setdefault("render", lambda self: self.render_inline("<div>x</div>", context={}))
        body.setdefault("photo", None)
        return type("Uploader", (LiveComponent,), body)

    def test_the_state_carries_the_note_rather_than_the_file(self):
        upload = store_temporarily(a_file())
        instance = self._component()("pb-test")
        instance.photo = upload

        self.assertEqual(instance._get_state()["photo"], upload.reference)

    def test_the_snapshot_can_be_signed_with_it(self):
        upload = store_temporarily(a_file())
        instance = self._component()("pb-test")
        instance.photo = upload

        self.assertIn("checksum", instance.serialize())

    def test_the_component_is_handed_the_file_again(self):
        upload = store_temporarily(a_file(name="holiday.txt"))

        instance = self._component().deserialize({"_id": "pb-test", "photo": upload.reference})

        self.assertIsInstance(instance.photo, TemporaryUpload)
        self.assertEqual(instance.photo.name, "holiday.txt")

    def test_a_note_worth_nothing_leaves_the_property_empty(self):
        instance = self._component().deserialize({"_id": "pb-test", "photo": "pyblade-upload:rubbish"})

        self.assertIsNone(instance.photo)

    def test_ordinary_text_is_left_as_it_is(self):
        instance = self._component(caption="").deserialize({"_id": "pb-test", "caption": "a photo"})

        self.assertEqual(instance.caption, "a photo")

    def test_the_file_is_given_to_the_form_that_checks_it(self):
        upload = store_temporarily(a_file(name="note.txt", content=b"hello"))
        cls = self._component(rules={"photo": forms.FileField()})
        instance = cls("pb-test")
        instance.photo = upload

        self.assertIs(instance.validate(), True)

    def test_a_file_the_rules_refuse_is_said_so(self):
        upload = store_temporarily(a_file(name="note.txt", content=b"x" * 3000))
        cls = self._component(rules={"photo": forms.FileField(validators=[MaxFileSize("1kb")])})
        instance = cls("pb-test")
        instance.photo = upload

        self.assertIs(instance.validate(), False)
        self.assertIn("photo", instance.errors)

    def test_a_component_asked_for_a_file_and_given_none_says_so(self):
        cls = self._component(rules={"photo": forms.FileField()})

        self.assertIs(cls("pb-test").validate(), False)

    def test_the_property_still_holds_the_upload_after_it_is_checked(self):
        """What the form made of a file is not what the action wants.

        Checking writes back what the form made of each value, so that an
        action works with a number rather than the text the page sent. A file
        is the one thing a form gives back worse than it was handed: an open
        file, with nowhere to be kept. The property keeps the upload.
        """
        upload = store_temporarily(a_file(name="note.txt", content=b"hello"))
        cls = self._component(rules={"photo": forms.FileField()})
        instance = cls("pb-test")
        instance.photo = upload

        instance.validate()

        self.assertIsInstance(instance.photo, TemporaryUpload)
        self.assertEqual(instance.photo.reference, upload.reference)

    def test_a_file_already_sent_survives_something_else_being_wrong(self):
        """The reader fixes the caption; the photo does not go up again."""
        upload = store_temporarily(a_file(name="note.txt", content=b"hello"))
        cls = self._component(
            caption="",
            rules={"photo": forms.FileField(), "caption": forms.CharField(max_length=5)},
        )
        instance = cls("pb-test")
        instance.photo = upload
        instance.caption = "far too long for this"

        self.assertIs(instance.validate(), False)
        self.assertEqual(instance._get_state()["photo"], upload.reference)


class TestSeeingTheFileBeforeItIsKept(UploadTestCase):
    """A file on its way can be shown, without being left where anyone may read it."""

    def test_where_it_can_be_seen_is_a_view_of_pyblades_own(self):
        upload = store_temporarily(a_file(name="holiday.png"))

        self.assertTrue(upload.url.startswith("/pyblade/live/preview/"))

    def test_it_is_not_sitting_under_the_media_path(self):
        upload = store_temporarily(a_file(name="holiday.png"))

        self.assertNotIn(upload.stored_name, upload.url)

    def test_what_the_page_is_given_is_the_note_it_already_holds(self):
        upload = store_temporarily(a_file(name="holiday.png"))

        self.assertIn(upload.reference[len("pyblade-upload:"):], upload.url)

    def test_a_template_may_show_it_without_a_directive_of_its_own(self):
        """The property holds a real file, so a preview is an ordinary img."""
        upload = store_temporarily(a_file(name="holiday.png"))
        cls = type("Uploader", (LiveComponent,), {
            "photo": None,
            "render": lambda self: self.render_inline(
                '<img src="{{ photo.url }}">', context={"photo": self.photo}
            ),
        })
        instance = cls("pb-test")
        instance.photo = upload

        self.assertIn(f'src="{upload.url}"', instance.render())


class TestAskingForSeveralFiles(UploadTestCase):
    """Django has a field for one file and none for several, so PyBlade brings one."""

    def test_several_files_come_through_as_several(self):
        field = MultipleFileField()

        cleaned = field.clean([a_file("one.txt"), a_file("two.txt")], None)

        self.assertEqual([file.name for file in cleaned], ["one.txt", "two.txt"])

    def test_one_file_comes_through_as_a_list_of_one(self):
        field = MultipleFileField()

        self.assertEqual(len(field.clean([a_file("one.txt")], None)), 1)

    def test_every_file_is_held_to_what_the_field_says(self):
        field = MultipleFileField(validators=[MaxFileSize("1kb")])

        with self.assertRaises(ValidationError):
            field.clean([a_file(content=b"x" * 10), a_file(content=b"x" * 3000)], None)

    def test_asking_for_files_and_being_given_none_is_refused(self):
        field = MultipleFileField()

        with self.assertRaises(ValidationError):
            field.clean([], None)

    def test_unless_it_says_it_does_not_need_any(self):
        field = MultipleFileField(required=False)

        self.assertEqual(field.clean([], None), [])

    def test_a_property_holding_several_files_travels_as_several_notes(self):
        uploads = [store_temporarily(a_file("one.txt")), store_temporarily(a_file("two.txt"))]
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })
        instance = cls("pb-test")
        instance.photos = uploads

        self.assertEqual(
            instance._get_state()["photos"], [upload.reference for upload in uploads]
        )

    def test_the_component_is_handed_the_files_again(self):
        uploads = [store_temporarily(a_file("one.txt")), store_temporarily(a_file("two.txt"))]
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })

        instance = cls.deserialize({
            "_id": "pb-test", "photos": [upload.reference for upload in uploads]
        })

        self.assertEqual([photo.name for photo in instance.photos], ["one.txt", "two.txt"])

    def test_a_list_of_ordinary_text_is_left_as_it_is(self):
        cls = type("Uploader", (LiveComponent,), {
            "tags": [],
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })

        instance = cls.deserialize({"_id": "pb-test", "tags": ["one", "two"]})

        self.assertEqual(instance.tags, ["one", "two"])

    def test_the_files_are_given_to_the_form_that_checks_them(self):
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "rules": {"photos": MultipleFileField()},
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })
        instance = cls("pb-test")
        instance.photos = [store_temporarily(a_file("one.txt")), store_temporarily(a_file("two.txt"))]

        self.assertIs(instance.validate(), True)

    def test_one_file_the_rules_refuse_refuses_the_lot(self):
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "rules": {"photos": MultipleFileField(validators=[MaxFileSize("1kb")])},
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })
        instance = cls("pb-test")
        instance.photos = [
            store_temporarily(a_file("one.txt")),
            store_temporarily(a_file("two.txt", content=b"x" * 3000)),
        ]

        self.assertIs(instance.validate(), False)
        self.assertIn("too big", instance.errors["photos"][0])

    def test_the_property_still_holds_the_files_after_they_are_checked(self):
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "rules": {"photos": MultipleFileField()},
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })
        instance = cls("pb-test")
        instance.photos = [store_temporarily(a_file("one.txt"))]

        instance.validate()

        self.assertIsInstance(instance.photos[0], TemporaryUpload)

    def test_a_template_may_show_them_all(self):
        uploads = [store_temporarily(a_file("one.png")), store_temporarily(a_file("two.png"))]
        cls = type("Uploader", (LiveComponent,), {
            "photos": [],
            "render": lambda self: self.render_inline(
                "@for(photo in photos)<img src=\"{{ photo.url }}\">@endfor", context={}
            ),
        })
        instance = cls("pb-test")
        instance.photos = uploads

        rendered = instance.render()

        for upload in uploads:
            self.assertIn(f'src="{upload.url}"', rendered)


class TestANoteTheClientHandsBack(UploadTestCase):
    """A note set from the page is the file, the same as one deserialized."""

    def _component(self, **body):
        body.setdefault("photo", None)
        body.setdefault("photos", [])
        body.setdefault("render", lambda self: self.render_inline(
            '<div><img src="{{ photo.url }}">@for(p in photos)<img src="{{ p.url }}">@endfor</div>',
            context={},
        ))
        return type("Uploader", (LiveComponent,), body)

    def test_one_set_from_the_page_is_the_file(self):
        upload = store_temporarily(a_file(name="holiday.png"))
        cls = self._component()

        answer = cls.update_component({"_id": "pb-test"}, "$set", ["photo", upload.reference])

        self.assertIn(f'src="{upload.url}"', answer["html"])

    def test_several_set_from_the_page_are_the_files(self):
        uploads = [store_temporarily(a_file("one.png")), store_temporarily(a_file("two.png"))]
        cls = self._component()

        answer = cls.update_component(
            {"_id": "pb-test"}, "$set", ["photos", [upload.reference for upload in uploads]]
        )

        for upload in uploads:
            self.assertIn(f'src="{upload.url}"', answer["html"])

    def test_what_the_page_holds_and_has_not_sent_is_the_file_too(self):
        upload = store_temporarily(a_file(name="holiday.png"))
        cls = self._component()

        answer = cls.update_component(
            {"_id": "pb-test"}, "$refresh", [], updates={"photo": upload.reference}
        )

        self.assertIn(f'src="{upload.url}"', answer["html"])


class TestThrowingAwayWhatNobodyKept(UploadTestCase):
    """A file nobody came back for cannot be claimed, and is not kept for ever."""

    def _age(self, upload, seconds):
        """Make a file as old as the test needs it to be."""
        path = self.media / upload.stored_name
        old = time.time() - seconds
        os.utime(path, (old, old))

    def test_a_file_too_old_to_be_claimed_is_thrown_away(self):
        upload = store_temporarily(a_file())
        self._age(upload, MAX_AGE + 60)

        sweep_temporary_uploads()

        self.assertFalse(default_storage.exists(upload.stored_name))

    def test_one_that_may_still_be_claimed_is_left_alone(self):
        upload = store_temporarily(a_file())
        self._age(upload, MAX_AGE - 60)

        sweep_temporary_uploads()

        self.assertTrue(default_storage.exists(upload.stored_name))

    def test_how_many_went_is_answered(self):
        for _ in range(3):
            self._age(store_temporarily(a_file()), MAX_AGE + 60)
        store_temporarily(a_file())

        self.assertEqual(sweep_temporary_uploads(), 3)

    def test_the_age_may_be_said(self):
        upload = store_temporarily(a_file())

        sweep_temporary_uploads(older_than=0)

        self.assertFalse(default_storage.exists(upload.stored_name))

    def test_a_file_whose_age_cannot_be_read_is_left_where_it_is(self):
        upload = store_temporarily(a_file())

        with mock.patch.object(default_storage, "get_modified_time", side_effect=NotImplementedError):
            self.assertEqual(sweep_temporary_uploads(older_than=0), 0)

        self.assertTrue(default_storage.exists(upload.stored_name))

    def test_nothing_kept_yet_is_nothing_to_throw_away(self):
        self.assertEqual(sweep_temporary_uploads(), 0)


class TestHowOftenItIsSwept(UploadTestCase):
    """Sweeping is worth doing now and then, not on every file that arrives."""

    def setUp(self):
        super().setUp()
        uploads_module._last_swept = None

    def tearDown(self):
        uploads_module._last_swept = None
        super().tearDown()

    def test_the_first_file_of_a_process_sweeps(self):
        upload = store_temporarily(a_file())
        self._make_stale(upload)

        self.assertEqual(sweep_if_due(), 1)

    def test_the_next_one_along_does_not_sweep_again(self):
        sweep_if_due()

        upload = store_temporarily(a_file())
        self._make_stale(upload)

        self.assertIsNone(sweep_if_due())
        self.assertTrue(default_storage.exists(upload.stored_name))

    def test_it_sweeps_again_once_the_while_has_passed(self):
        sweep_if_due()

        upload = store_temporarily(a_file())
        self._make_stale(upload)

        self.assertEqual(sweep_if_due(every=0), 1)

    def _make_stale(self, upload):
        path = self.media / upload.stored_name
        old = time.time() - (MAX_AGE + 60)
        os.utime(path, (old, old))
