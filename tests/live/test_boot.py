"""boot(): what a component sets up every time it is brought to life.

A component is built again for every request, from the snapshot the page holds,
and mount() only ran for the first of them. What cannot travel in a snapshot, a
client, a queryset, anything the component keeps under a private name, has to be
made again each time; boot() is where.
"""

import unittest

from pyblade.live import LiveComponent, lazy
from pyblade.live.testing import live

LOG = []


class Hooked(LiveComponent):
    count = 0

    def mount(self):
        LOG.append("mount")

    def boot(self):
        LOG.append("boot")
        self._client = "built"

    def hydrate(self):
        LOG.append("hydrate")

    def increment(self):
        LOG.append(f"action:{getattr(self, '_client', 'missing')}")
        self.count += 1

    def render(self):
        return self.render_inline("<div>{{ count }}</div>")


@lazy
class Slow(Hooked):
    pass


class BootTestCase(unittest.TestCase):
    def setUp(self):
        LOG.clear()


class TestTheFirstRendering(BootTestCase):
    def test_it_runs_once_the_component_is_mounted(self):
        live(Hooked)

        self.assertEqual(LOG, ["mount", "boot"])


class TestEveryLaterRequest(BootTestCase):
    def test_it_runs_before_hydrate_and_before_the_action(self):
        counter = live(Hooked)
        LOG.clear()

        counter.call("increment")

        self.assertEqual(LOG, ["boot", "hydrate", "action:built"])

    def test_it_runs_again_for_each_request(self):
        counter = live(Hooked)
        LOG.clear()

        counter.call("increment")
        counter.call("increment")

        self.assertEqual(LOG.count("boot"), 2)

    def test_it_runs_for_a_request_that_only_asks_for_a_new_rendering(self):
        counter = live(Hooked)
        LOG.clear()

        counter.refresh()

        self.assertEqual(LOG, ["boot", "hydrate"])

    def test_it_runs_for_a_property_the_page_sets(self):
        counter = live(Hooked)
        LOG.clear()

        counter.set("count", 3)

        self.assertEqual(LOG, ["boot", "hydrate"])

    def test_mount_does_not_run_again(self):
        counter = live(Hooked)
        LOG.clear()

        counter.call("increment")

        self.assertNotIn("mount", LOG)

    def test_what_it_builds_under_a_private_name_is_not_state(self):
        counter = live(Hooked)

        counter.call("increment")

        self.assertEqual(sorted(counter.state), ["count"])


class TestALazyComponent(BootTestCase):
    def test_nothing_runs_while_it_waits(self):
        live(Slow, load=False)

        self.assertEqual(LOG, [])

    def test_it_runs_once_when_the_component_is_loaded(self):
        slow = live(Slow, load=False)

        slow.load()

        self.assertEqual(LOG, ["mount", "boot", "hydrate"])

    def test_it_runs_on_the_requests_after_that_load(self):
        slow = live(Slow)
        LOG.clear()

        slow.call("increment")

        self.assertEqual(LOG, ["boot", "hydrate", "action:built"])


if __name__ == "__main__":
    unittest.main()
