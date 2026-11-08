"""A value that is only worked out when a template reads it.

A component keeps what it can rebuild out of what it sends to the page, and has
it in its template all the same. Some of those values cost something to build, so
they are built when the template asks for them and not before.
"""

import unittest

from pyblade.engine.contexts import LazyValue
from pyblade.engine.processor import TemplateProcessor


class Counting:
    """A getter that remembers how many times it was asked."""

    def __init__(self, value):
        self.value = value
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.value


class TestReadingALazyValue(unittest.TestCase):
    def render(self, template, **context):
        return TemplateProcessor().render(template, context)

    def test_a_template_reads_the_value_it_stands_for(self):
        self.assertEqual(self.render("{{ count }}", count=LazyValue(lambda: 5)), "5")

    def test_it_can_be_used_in_an_expression(self):
        self.assertEqual(self.render("{{ count + 1 }}", count=LazyValue(lambda: 5)), "6")

    def test_it_can_be_looped_over(self):
        result = self.render("@for(n in numbers){{ n }},@endfor", numbers=LazyValue(lambda: [1, 2, 3]))

        self.assertEqual(result, "1,2,3,")

    def test_an_attribute_of_it_can_be_read(self):
        class Thing:
            label = "thing"

        self.assertEqual(self.render("{{ thing.label }}", thing=LazyValue(Thing)), "thing")

    def test_it_is_worked_out_once_however_often_it_is_read(self):
        getter = Counting([1, 2])

        self.render("@for(n in numbers){{ n }}@endfor@for(n in numbers){{ n }}@endfor", numbers=LazyValue(getter))

        self.assertEqual(getter.calls, 1)

    def test_it_is_not_worked_out_when_nothing_reads_it(self):
        getter = Counting(1)

        self.render("@if(False){{ count }}@endif", count=LazyValue(getter))

        self.assertEqual(getter.calls, 0)

    def test_it_is_not_worked_out_by_being_in_the_context(self):
        getter = Counting(1)

        self.render("nothing here", count=LazyValue(getter), other=2)

        self.assertEqual(getter.calls, 0)

    def test_a_value_that_is_not_lazy_is_read_as_it_always_was(self):
        self.assertEqual(self.render("{{ count }}", count=5), "5")


class TestALazyValueItself(unittest.TestCase):
    def test_it_does_not_work_itself_out_to_describe_itself(self):
        getter = Counting(1)

        repr(LazyValue(getter))
        str(LazyValue(getter))

        self.assertEqual(getter.calls, 0)

    def test_resolving_it_gives_the_value(self):
        self.assertEqual(LazyValue(lambda: "x").resolve(), "x")

    def test_what_it_stands_for_may_be_none(self):
        getter = Counting(None)
        lazy = LazyValue(getter)

        self.assertIsNone(lazy.resolve())
        self.assertIsNone(lazy.resolve())
        self.assertEqual(getter.calls, 1)


if __name__ == "__main__":
    unittest.main()
