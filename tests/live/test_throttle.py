"""Keeping one client from taking the live endpoints for itself.

A page only has to be loaded once to hand a browser a snapshot it can send back
as often as it likes. What is checked here is that it cannot do so faster than
the project allows, cannot send more than an answer ever needs, and cannot tie
up the server's threads by asking for streamed actions all at once.
"""

import unittest
from unittest import mock

from django.test import RequestFactory

from pyblade.config import settings
from pyblade.live import throttle
from pyblade.live.throttle import (
    client_of,
    hit,
    parse_rate,
    parse_size,
    stream_slots,
    throttled,
)


def endpoint(request):
    from django.http import JsonResponse

    return JsonResponse({"ok": True})


class ThrottleTestCase(unittest.TestCase):
    def setUp(self):
        self.requests = RequestFactory()
        self._saved = settings._data.get("live")
        self.configure()

    def tearDown(self):
        if self._saved is None:
            settings._data.pop("live", None)
        else:
            settings._data["live"] = self._saved

    def configure(self, **options):
        live = dict(self._saved or {})
        live["throttle"] = options
        settings._data["live"] = live

    def post(self, address="10.0.0.1", body="{}", **extra):
        return self.requests.post(
            "/pyblade/live/",
            data=body,
            content_type="application/json",
            REMOTE_ADDR=address,
            **extra,
        )


class TestReadingWhatTheProjectSays(unittest.TestCase):
    def test_a_rate_is_written_the_way_people_write_one(self):
        self.assertEqual(parse_rate("120/minute"), (120, 60))
        self.assertEqual(parse_rate("5/second"), (5, 1))
        self.assertEqual(parse_rate("1000 / hours"), (1000, 3600))

    def test_a_rate_it_cannot_read_is_refused_at_once(self):
        with self.assertRaises(ValueError):
            parse_rate("lots")

    def test_a_size_is_written_the_way_people_write_one(self):
        self.assertEqual(parse_size("1mb"), 1024**2)
        self.assertEqual(parse_size("500kb"), 500 * 1024)
        self.assertEqual(parse_size(2048), 2048)


class TestCountingRequests(ThrottleTestCase):
    def test_a_client_within_the_rate_is_let_through(self):
        self.configure(actions="3/minute")

        self.assertEqual([hit("actions", self.post()) for _ in range(3)], [None, None, None])

    def test_the_request_after_is_refused(self):
        self.configure(actions="3/minute")
        for _ in range(3):
            hit("actions", self.post())

        self.assertIsNotNone(hit("actions", self.post()))

    def test_it_is_told_how_long_to_wait(self):
        self.configure(actions="1/minute")

        with mock.patch.object(throttle, "_now", return_value=6000 + 15):
            hit("actions", self.post())
            wait = hit("actions", self.post())

        self.assertEqual(wait, 45)

    def test_the_count_starts_again_once_the_time_has_passed(self):
        self.configure(actions="1/minute")

        with mock.patch.object(throttle, "_now", return_value=6000):
            hit("actions", self.post())
            self.assertIsNotNone(hit("actions", self.post()))

        with mock.patch.object(throttle, "_now", return_value=6060):
            self.assertIsNone(hit("actions", self.post()))

    def test_each_client_is_counted_on_its_own(self):
        self.configure(actions="1/minute")
        hit("actions", self.post(address="10.0.0.1"))

        self.assertIsNone(hit("actions", self.post(address="10.0.0.2")))

    def test_each_endpoint_is_counted_on_its_own(self):
        self.configure(actions="1/minute", uploads="1/minute")
        hit("actions", self.post())

        self.assertIsNone(hit("uploads", self.post()))


class TestWhoIsAsking(ThrottleTestCase):
    def test_someone_signed_in_is_counted_as_themselves(self):
        request = self.post(address="10.0.0.1")
        request.user = mock.Mock(is_authenticated=True, pk=7)

        self.assertEqual(client_of(request), "user:7")

    def test_anyone_else_by_the_address_they_came_from(self):
        request = self.post(address="10.0.0.1")
        request.user = mock.Mock(is_authenticated=False)

        self.assertEqual(client_of(request), "ip:10.0.0.1")

    def test_what_a_request_says_it_was_forwarded_for_is_not_believed_by_default(self):
        """Believed, it would let every request name itself something new."""
        request = self.post(address="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4")

        self.assertEqual(client_of(request), "ip:10.0.0.1")

    def test_it_is_believed_behind_a_proxy_the_project_trusts(self):
        self.configure(trust_forwarded=True)
        request = self.post(address="10.0.0.1", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1")

        self.assertEqual(client_of(request), "ip:1.2.3.4")


class TestTheGuardOnAnEndpoint(ThrottleTestCase):
    def test_a_request_within_the_rate_is_answered(self):
        self.assertEqual(throttled("actions")(endpoint)(self.post()).status_code, 200)

    def test_one_too_many_is_answered_429(self):
        self.configure(actions="2/minute")
        guarded = throttled("actions")(endpoint)
        guarded(self.post())
        guarded(self.post())

        response = guarded(self.post())

        self.assertEqual(response.status_code, 429)
        self.assertTrue(response["Retry-After"].isdigit())

    def test_a_request_bigger_than_an_answer_needs_is_refused_unread(self):
        self.configure(max_body="1kb")

        response = throttled("actions")(endpoint)(self.post(body="x" * 4096))

        self.assertEqual(response.status_code, 413)

    def test_the_size_may_be_left_to_the_endpoint(self):
        """A file's size is the component's to decide, with MaxFileSize."""
        self.configure(max_body="1kb")

        response = throttled("uploads", check_size=False)(endpoint)(self.post(body="x" * 4096))

        self.assertEqual(response.status_code, 200)

    def test_a_project_may_turn_it_off(self):
        self.configure(enabled=False, actions="1/minute")
        guarded = throttled("actions")(endpoint)
        guarded(self.post())

        self.assertEqual(guarded(self.post()).status_code, 200)


class TestStreamedActionsAtOnce(ThrottleTestCase):
    def tearDown(self):
        while stream_slots.running:
            stream_slots.give_back()
        super().tearDown()

    def test_only_so_many_may_run(self):
        self.configure(max_streams=2)

        self.assertEqual([stream_slots.take() for _ in range(3)], [True, True, False])

    def test_one_that_ends_makes_room_for_the_next(self):
        self.configure(max_streams=1)
        stream_slots.take()

        stream_slots.give_back()

        self.assertTrue(stream_slots.take())


class TestTheLiveEndpointItself(ThrottleTestCase):
    """The guard is on the endpoints PyBlade answers on, not only on paper."""

    def test_the_actions_endpoint_is_guarded(self):
        from pyblade.live.views import update_component

        self.configure(actions="1/minute")
        update_component(self.post(body='{"snapshot": {}}'))

        self.assertEqual(update_component(self.post(body='{"snapshot": {}}')).status_code, 429)

    def test_the_upload_endpoint_is_guarded(self):
        from pyblade.live.views import upload_file

        self.configure(uploads="1/minute")
        upload_file(self.requests.post("/pyblade/live/upload/", {}, REMOTE_ADDR="10.0.0.1"))

        response = upload_file(self.requests.post("/pyblade/live/upload/", {}, REMOTE_ADDR="10.0.0.1"))

        self.assertEqual(response.status_code, 429)

    def test_a_streamed_answer_that_never_starts_gives_its_slot_back(self):
        """A client gone before the answer started would otherwise hold it for ever."""
        from pyblade.live.views import _HoldingASlot

        self.configure(max_streams=1)
        stream_slots.take()

        def never_iterated():
            yield "unreachable"

        _HoldingASlot(never_iterated()).close()

        self.assertTrue(stream_slots.take())
