"""What a component shows while it is still being got ready.

A lazy component does none of its work on the first pass, so there is nothing
to show and something has to stand in its place. What stands there is drawn
from a shape and a number of lines rather than written by hand, so that making
a component lazy is a decorator and nothing else.
"""

import re
import unittest

from pyblade.live.skeleton import skeleton_markup


def lines_of(markup):
    return re.findall(r'class="pb-skeleton-line"[^>]*style="width:\s*([\d.]+)%"', markup)


class TestWhatIsDrawn(unittest.TestCase):
    def test_it_says_it_is_busy(self):
        self.assertIn('aria-busy="true"', skeleton_markup())

    def test_it_names_no_component_of_its_own(self):
        """It is markup; the id lands on it when the component renders it."""
        self.assertNotIn("pb:id", skeleton_markup())

    def test_it_is_three_lines_unless_another_number_is_asked_for(self):
        self.assertEqual(len(lines_of(skeleton_markup())), 3)

    def test_as_many_lines_as_were_asked_for(self):
        self.assertEqual(len(lines_of(skeleton_markup(lines=6))), 6)

    def test_the_lines_are_not_all_the_same_length(self):
        """A stack of identical bars reads as a table, not as text."""
        widths = lines_of(skeleton_markup(lines=4))

        self.assertGreater(len(set(widths)), 1)

    def test_the_last_line_is_the_short_one(self):
        widths = [float(width) for width in lines_of(skeleton_markup(lines=4))]

        self.assertLess(widths[-1], widths[0])

    def test_one_line_is_a_line(self):
        self.assertEqual(len(lines_of(skeleton_markup(lines=1))), 1)


class TestTheShapes(unittest.TestCase):
    def test_text_is_what_it_draws_unless_told_otherwise(self):
        self.assertNotIn("pb-skeleton-block", skeleton_markup())

    def test_a_card_has_something_above_its_lines(self):
        markup = skeleton_markup(shape="card")

        self.assertIn("pb-skeleton-block", markup)
        self.assertEqual(len(lines_of(markup)), 3)

    def test_a_table_is_rows_of_cells(self):
        markup = skeleton_markup(shape="table", lines=4)

        self.assertEqual(markup.count("pb-skeleton-row"), 4)
        self.assertGreater(markup.count("pb-skeleton-cell"), 4)

    def test_a_shape_it_cannot_draw_is_said_so_outright(self):
        with self.assertRaises(ValueError) as caught:
            skeleton_markup(shape="tabel")

        self.assertIn("tabel", str(caught.exception))

    def test_a_number_of_lines_that_is_no_number_of_lines_is_refused(self):
        with self.assertRaises(ValueError):
            skeleton_markup(lines=0)
