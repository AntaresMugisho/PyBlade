"""What a live component pushes, when it is rendered again after an action.

An update has no layout around it, so there is no stack for a push to land in.
What was pushed is sent with the answer instead, and the client adds to the page
what it does not already hold.
"""

import unittest

from pyblade.engine import stacks
from pyblade.live.base import LiveComponent


class Chart(LiveComponent):
    shown = False

    def show(self):
        self.shown = True

    def render(self):
        return self.render_inline(
            "<div>@if(shown)<canvas></canvas>"
            "@push('scripts')<script src=\"/chart.js\"></script>@endpush@endif</div>",
            context={},
        )


class TestPushesOnUpdate(unittest.TestCase):
    def update(self, action):
        state = Chart.deserialize({}).serialize()["state"]
        return Chart.update_component(state, action, [])

    def test_what_is_pushed_is_sent_with_the_answer(self):
        answer = self.update("show")

        self.assertEqual(answer["pushes"], [{
            "stack": "scripts",
            "key": stacks.key_of('<script src="/chart.js"></script>'),
            "html": '<script src="/chart.js"></script>',
        }])

    def test_it_is_not_in_the_markup(self):
        self.assertNotIn("chart.js", self.update("show")["html"])

    def test_an_answer_that_pushed_nothing_says_nothing_about_it(self):
        self.assertNotIn("pushes", self.update("$refresh"))

    def test_the_first_render_pushes_into_the_page(self):
        with stacks.collecting() as collection:
            Chart.render_initial({"shown": True})

        self.assertEqual([push["stack"] for push in collection.pushes_for_client()], ["scripts"])
