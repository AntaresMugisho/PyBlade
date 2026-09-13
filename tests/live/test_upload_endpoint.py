"""The request a file arrives on.

A file is sent on its own, before any action runs, so that it can be watched
while it goes and stopped part way. What arrives is checked against what the
component expects of the property it is for -- and refused before its bytes are
kept, not after -- and what goes back is a note the page can hand on.
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

from django import forms
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, override_settings

from pyblade.live.base import LiveComponent
from pyblade.live import uploads as uploads_module
from pyblade.live.registry import registry
from pyblade.live.uploads import MaxFileSize, MultipleFileField, TemporaryUpload
from pyblade.live.views import upload_file


class Uploader(LiveComponent):
    photo = None
    photos = []
    caption = ""

    rules = {
        "photo": forms.FileField(validators=[MaxFileSize("1kb")]),
        "photos": MultipleFileField(validators=[MaxFileSize("1kb")]),
        "caption": forms.CharField(required=False),
    }

    def render(self):
        return self.render_inline("<div>{{ caption }}</div>", context={})


class UploadEndpointTestCase(unittest.TestCase):
    def setUp(self):
        self.media = Path(tempfile.mkdtemp())
        self.override = override_settings(MEDIA_ROOT=str(self.media), MEDIA_URL="/media/")
        self.override.enable()

        self.path = f"{__name__}.Uploader"
        registry.register(self.path, Uploader)

        self.requests = RequestFactory()

    def tearDown(self):
        self.override.disable()
        registry._components.pop(self.path, None)
        shutil.rmtree(self.media, ignore_errors=True)

    def _snapshot(self, component_class=None):
        instance = (component_class or Uploader)("pb-test")
        snapshot = instance.serialize()
        snapshot["class"] = self.path

        # The class is part of what is signed, so it is signed again having changed
        from pyblade.live.security import generate_checksum

        snapshot.pop("checksum")
        snapshot["checksum"] = generate_checksum(snapshot)

        return snapshot

    def _post(self, file, property_name="photo", snapshot=None):
        request = self.requests.post("/pyblade/live/upload/", {
            "file": file if isinstance(file, list) else [file],
            "property": property_name,
            "snapshot": json.dumps(snapshot if snapshot is not None else self._snapshot()),
        })

        return upload_file(request)

    def _body(self, response):
        return json.loads(b"".join(response).decode() if hasattr(response, "streaming_content")
                          else response.content.decode())


class TestSendingAFile(UploadEndpointTestCase):
    def test_a_file_is_taken(self):
        response = self._post(SimpleUploadedFile("note.txt", b"hello"))

        self.assertEqual(response.status_code, 200)

    def test_what_comes_back_is_a_note_the_page_can_hand_on(self):
        body = self._body(self._post(SimpleUploadedFile("note.txt", b"hello")))

        upload = TemporaryUpload.from_reference(body["files"][0]["reference"])

        self.assertIsNotNone(upload)
        self.assertEqual(upload.open().read(), b"hello")

    def test_what_the_file_was_called_comes_back_with_it(self):
        body = self._body(self._post(SimpleUploadedFile("holiday.txt", b"sun")))

        self.assertEqual(body["files"][0]["name"], "holiday.txt")
        self.assertEqual(body["files"][0]["size"], 3)

    def test_the_file_is_not_kept_where_it_will_stay(self):
        self._post(SimpleUploadedFile("note.txt", b"hello"))

        self.assertTrue((self.media / "pyblade-tmp").is_dir())


class TestRefusingWhatShouldNotBeKept(UploadEndpointTestCase):
    def test_a_file_over_the_size_the_component_allows_is_refused(self):
        response = self._post(SimpleUploadedFile("big.txt", b"x" * 4000))

        self.assertEqual(response.status_code, 422)
        self.assertIn("too big", self._body(response)["errors"][0])

    def test_its_bytes_are_not_kept(self):
        self._post(SimpleUploadedFile("big.txt", b"x" * 4000))

        temporary = self.media / "pyblade-tmp"
        self.assertFalse(temporary.exists() and any(temporary.iterdir()))

    def test_a_property_that_takes_no_file_is_refused(self):
        response = self._post(SimpleUploadedFile("note.txt", b"hello"), property_name="caption")

        self.assertEqual(response.status_code, 422)

    def test_a_property_the_component_says_nothing_about_is_refused(self):
        response = self._post(SimpleUploadedFile("note.txt", b"hello"), property_name="nowhere")

        self.assertEqual(response.status_code, 422)

    def test_the_machinery_of_a_component_may_not_be_uploaded_to(self):
        response = self._post(SimpleUploadedFile("note.txt", b"hello"), property_name="template_name")

        self.assertEqual(response.status_code, 422)

    def test_a_request_carrying_no_file_is_refused(self):
        request = self.requests.post("/pyblade/live/upload/", {
            "property": "photo",
            "snapshot": json.dumps(self._snapshot()),
        })

        self.assertEqual(upload_file(request).status_code, 400)


class TestWhoMaySend(UploadEndpointTestCase):
    """A file is taken from a page PyBlade rendered, and from nowhere else."""

    def test_a_snapshot_that_was_written_over_is_refused(self):
        snapshot = self._snapshot()
        snapshot["state"]["caption"] = "changed behind the server's back"

        response = self._post(SimpleUploadedFile("note.txt", b"hello"), snapshot=snapshot)

        self.assertEqual(response.status_code, 400)

    def test_a_request_with_no_snapshot_at_all_is_refused(self):
        request = self.requests.post("/pyblade/live/upload/", {
            "file": SimpleUploadedFile("note.txt", b"hello"),
            "property": "photo",
        })

        self.assertEqual(upload_file(request).status_code, 400)

    def test_a_snapshot_naming_a_component_that_does_not_exist_is_refused(self):
        snapshot = self._snapshot()
        snapshot["class"] = "nowhere.Nothing"

        from pyblade.live.security import generate_checksum

        snapshot.pop("checksum")
        snapshot["checksum"] = generate_checksum(snapshot)

        response = self._post(SimpleUploadedFile("note.txt", b"hello"), snapshot=snapshot)

        self.assertEqual(response.status_code, 404)


class TestSendingSeveralFilesAtOnce(UploadEndpointTestCase):
    """One choosing is one request, so what comes back is one list."""

    def test_every_file_comes_back(self):
        body = self._body(self._post(
            [SimpleUploadedFile("one.txt", b"a"), SimpleUploadedFile("two.txt", b"b")],
            property_name="photos",
        ))

        self.assertEqual([file["name"] for file in body["files"]], ["one.txt", "two.txt"])

    def test_each_note_holds_its_own_file(self):
        body = self._body(self._post(
            [SimpleUploadedFile("one.txt", b"a"), SimpleUploadedFile("two.txt", b"b")],
            property_name="photos",
        ))

        kept = [TemporaryUpload.from_reference(file["reference"]).open().read()
                for file in body["files"]]

        self.assertEqual(kept, [b"a", b"b"])

    def test_one_file_the_rules_refuse_refuses_the_lot(self):
        response = self._post(
            [SimpleUploadedFile("one.txt", b"a"), SimpleUploadedFile("big.txt", b"x" * 4000)],
            property_name="photos",
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("too big", self._body(response)["errors"][0])

    def test_nothing_of_a_refused_lot_is_kept(self):
        self._post(
            [SimpleUploadedFile("one.txt", b"a"), SimpleUploadedFile("big.txt", b"x" * 4000)],
            property_name="photos",
        )

        temporary = self.media / "pyblade-tmp"
        self.assertFalse(temporary.exists() and any(temporary.iterdir()))

    def test_a_property_that_asks_for_one_file_is_not_given_several(self):
        response = self._post(
            [SimpleUploadedFile("one.txt", b"a"), SimpleUploadedFile("two.txt", b"b")],
            property_name="photo",
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("one file", self._body(response)["errors"][0])



class TestShowingAFileOnItsWay(UploadEndpointTestCase):
    """What a preview reads from, before anything has been kept for good."""

    def _upload(self, name="holiday.png", content=b"a picture", content_type="image/png"):
        from pyblade.live.uploads import store_temporarily

        return store_temporarily(SimpleUploadedFile(name, content, content_type=content_type))

    def _get(self, token):
        from pyblade.live.views import preview_upload

        return preview_upload(self.requests.get(f"/pyblade/live/preview/{token}/"), token)

    def _token(self, upload):
        from pyblade.live.uploads import REFERENCE_PREFIX

        return upload.reference[len(REFERENCE_PREFIX):]

    def test_the_file_is_handed_over(self):
        upload = self._upload(content=b"a picture")

        response = self._get(self._token(upload))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"a picture")

    def test_it_is_served_as_what_it_was_stored_as(self):
        response = self._get(self._token(self._upload(content_type="image/png")))

        self.assertEqual(response["Content-Type"], "image/png")

    def test_it_is_not_for_anyone_else_to_keep(self):
        response = self._get(self._token(self._upload()))

        self.assertIn("private", response["Cache-Control"])

    def test_a_note_made_up_out_of_nothing_shows_nothing(self):
        from django.http import Http404

        with self.assertRaises(Http404):
            self._get("rubbish")

    def test_a_note_whose_file_has_gone_shows_nothing(self):
        from django.http import Http404

        upload = self._upload()
        upload.delete()

        with self.assertRaises(Http404):
            self._get(self._token(upload))


class TestTidyingUpWhileTakingAFile(UploadEndpointTestCase):
    """Taking a file also throws away the ones nobody came back for."""

    def setUp(self):
        super().setUp()
        uploads_module._last_swept = None

    def tearDown(self):
        uploads_module._last_swept = None
        super().tearDown()

    def _stale_file(self):
        from pyblade.live.uploads import MAX_AGE, store_temporarily

        upload = store_temporarily(SimpleUploadedFile("forgotten.txt", b"nobody came back"))
        old = time.time() - (MAX_AGE + 60)
        os.utime(self.media / upload.stored_name, (old, old))

        return upload

    def test_a_file_nobody_came_back_for_is_thrown_away(self):
        forgotten = self._stale_file()

        self._post(SimpleUploadedFile("note.txt", b"hello"))

        self.assertFalse(default_storage.exists(forgotten.stored_name))

    def test_the_file_that_has_just_arrived_is_not(self):
        body = self._body(self._post(SimpleUploadedFile("note.txt", b"hello")))

        upload = TemporaryUpload.from_reference(body["files"][0]["reference"])

        self.assertTrue(default_storage.exists(upload.stored_name))

    def test_a_refused_file_still_leaves_the_place_tidier(self):
        forgotten = self._stale_file()

        self._post(SimpleUploadedFile("big.txt", b"x" * 4000))

        self.assertFalse(default_storage.exists(forgotten.stored_name))


# The endpoint resolves the component by the path it is registered under, which
# is this module's own name
sys.modules[__name__].Uploader = Uploader
