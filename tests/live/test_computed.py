"""Values a component derives from what it holds, and does not send to the page.

A queryset, a form, anything the browser could not hold: they are not state, they
are worked out from it. A computed value is the way to say so -- written as a
method, read as a property, available in the template by its name, and never
part of the snapshot.
"""

import json
import unittest

from pyblade.live import LiveComponent, computed
from pyblade.live.testing import live

CALLS = []


class Thing:
    """Something a snapshot could never carry."""

    label = "a thing"


class Posts(LiveComponent):
    search = ""

    @computed
    def titles(self):
        CALLS.append(self.search)
        return [title for title in ("alpha", "beta", "gamma") if self.search in title]

    @computed
    def never_read(self):
        CALLS.append("never_read")
        return 1

    @computed
    def thing(self):
        return Thing()

    @computed
    def numbers(self):
        return frozenset({7})

    def narrow(self):
        # Read before the property it depends on changes, as an action may well do
        self.before = list(self.titles)
        self.search = "be"

    def render(self):
        return self.render_inline(
            "<div>@for(t in titles){{ t }},@endfor|{{ thing.label }}|@for(n in numbers){{ n }}@endfor</div>"
        )


class Twice(Posts):
    def render(self):
        return self.render_inline("@for(t in titles){{ t }}@endfor@for(t in titles){{ t }}@endfor")


class ComputedTestCase(unittest.TestCase):
    def setUp(self):
        CALLS.clear()


class TestUsingAComputedValue(ComputedTestCase):
    def test_the_template_reads_it_by_its_name(self):
        live(Posts).assert_sees("alpha,beta,gamma,")

    def test_it_follows_what_it_is_worked_out_from(self):
        posts = live(Posts)

        posts.set("search", "al")

        posts.assert_sees("alpha,")
        posts.assert_does_not_see("beta")

    def test_python_reads_it_as_a_property(self):
        posts = Posts("pb-test")

        self.assertEqual(posts.titles, ["alpha", "beta", "gamma"])

    def test_it_may_be_something_json_cannot_hold(self):
        # It is rebuilt, not sent, so it does not have to travel
        posts = live(Posts)

        posts.assert_sees("a thing")
        posts.assert_sees("|7")

    def test_a_subclass_has_the_ones_of_its_parent(self):
        live(Twice).assert_sees("alphabetagammaalphabetagamma")


class TestWhatItIsNot(ComputedTestCase):
    def test_it_is_not_part_of_the_state(self):
        state = live(Posts).state

        self.assertEqual(sorted(state), ["search"])

    def test_it_is_not_in_the_snapshot_the_page_holds(self):
        snapshot = Posts("pb-test").serialize()

        self.assertNotIn("titles", json.dumps(snapshot))
        self.assertNotIn("thing", snapshot["state"])

    def test_it_is_not_an_action_the_page_may_call(self):
        with self.assertRaises((AttributeError, PermissionError)):
            live(Posts).call("titles")

    def test_the_page_may_not_set_it(self):
        with self.assertRaises(PermissionError):
            live(Posts).set("titles", ["x"])

    def test_it_cannot_be_assigned(self):
        posts = Posts("pb-test")

        with self.assertRaises(AttributeError):
            posts.titles = ["x"]


class TestWhenItIsWorkedOut(ComputedTestCase):
    def test_it_is_worked_out_once_however_often_it_is_read(self):
        posts = Posts("pb-test")

        posts.titles
        posts.titles

        self.assertEqual(CALLS, [""])

    def test_it_is_worked_out_once_for_a_template_using_it_twice(self):
        live(Twice)

        self.assertEqual(CALLS.count(""), 1)

    def test_it_is_not_worked_out_when_nothing_reads_it(self):
        live(Posts)

        self.assertNotIn("never_read", CALLS)

    def test_deleting_it_makes_the_next_read_work_it_out_again(self):
        posts = Posts("pb-test")

        posts.titles
        del posts.titles
        posts.titles

        self.assertEqual(CALLS, ["", ""])

    def test_deleting_one_that_was_never_read_is_harmless(self):
        posts = Posts("pb-test")

        del posts.titles

        self.assertEqual(CALLS, [])

    def test_the_page_is_never_shown_one_worked_out_before_the_state_changed(self):
        posts = live(Posts)

        posts.call("narrow")

        posts.assert_sees("beta,")
        posts.assert_does_not_see("alpha")
        self.assertEqual(posts.state["before"], ["alpha", "beta", "gamma"])


if __name__ == "__main__":
    unittest.main()
