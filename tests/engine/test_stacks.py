"""@stack and @push: content written anywhere, gathered where the layout says.

A push is kept once however many times it is made, so that a component used
twice on a page does not bring its script twice.
"""

import re

from pyblade.engine import stacks

from tests.engine.test_components import ComponentTestCase


def visible(html):
    """The output without the markers the client finds the stacks by."""
    return re.sub(r"<!--pb:(push|stack) [^>]*-->", "", html)


class TestStacks(ComponentTestCase):
    def test_a_push_lands_where_the_stack_is(self):
        html = self._render("<head>@stack('scripts')</head>@push('scripts')<script>a</script>@endpush<p>body</p>")

        self.assertEqual(visible(html), "<head><script>a</script></head><p>body</p>")

    def test_pushes_come_out_in_the_order_they_are_made(self):
        html = self._render(
            "@stack('s')"
            "@push('s')<i>1</i>@endpush"
            "@push('s')<i>2</i>@endpush"
            "@push('s')<i>3</i>@endpush"
        )

        self.assertEqual(visible(html), "<i>1</i><i>2</i><i>3</i>")

    def test_the_same_content_is_pushed_once(self):
        html = self._render("@stack('s')@push('s')<script>a</script>@endpush@push('s')  <script>a</script>\n@endpush")

        self.assertEqual(visible(html).count("<script>a</script>"), 1)

    def test_the_same_content_in_two_stacks_is_in_both(self):
        html = self._render("@stack('a')|@stack('b')@push('a')<i>x</i>@endpush@push('b')<i>x</i>@endpush")

        self.assertEqual(visible(html), "<i>x</i>|<i>x</i>")

    def test_a_stack_nothing_is_pushed_to_is_empty(self):
        self.assertEqual(visible(self._render("<head>@stack('styles')</head>")), "<head></head>")

    def test_a_push_to_a_stack_that_is_nowhere_is_dropped(self):
        self.assertEqual(visible(self._render("@push('nowhere')<i>x</i>@endpush<p>ok</p>")), "<p>ok</p>")

    def test_a_push_renders_with_the_context_it_is_written_in(self):
        html = self._render("@stack('s')@push('s')<i>{{ name }}</i>@endpush", {"name": "Ada"})

        self.assertEqual(visible(html), "<i>Ada</i>")

    def test_a_push_in_a_branch_not_taken_is_not_made(self):
        html = self._render("@stack('s')@if(False)@push('s')<i>x</i>@endpush@endif")

        self.assertEqual(visible(html), "")

    def test_a_child_template_pushes_into_its_layout(self):
        self._write(
            "layouts.base",
            "<head>@stack('scripts')</head><body>@block('content')@endblock</body>",
        )

        html = self._render(
            "@extends('layouts.base')"
            "@block('content')<p>page</p>@push('scripts')<script>page</script>@endpush@endblock"
        )

        self.assertEqual(visible(html), "<head><script>page</script></head><body><p>page</p></body>")

    def test_a_component_used_twice_pushes_its_script_once(self):
        self._component("chart", "<canvas></canvas>@push('scripts')<script src=\"/chart.js\"></script>@endpush")

        html = self._render("<head>@stack('scripts')</head><pb-chart /><pb-chart />")

        self.assertEqual(
            visible(html),
            '<head><script src="/chart.js"></script></head><canvas></canvas><canvas></canvas>',
        )

    def test_a_render_taken_from_the_cache_still_pushes(self):
        self._component("chart", "<canvas></canvas>@push('scripts')<script>chart</script>@endpush")
        page = "<head>@stack('scripts')</head><pb-chart />"

        self._render(page)
        self._render("<p>another page</p><pb-chart />")  # The component is rendered from cache
        html = self._render("@stack('scripts')<pb-chart />")

        self.assertIn("<script>chart</script>", visible(html))

    def test_the_stack_marks_its_end_and_each_push(self):
        html = self._render("@stack('scripts')@push('scripts')<i>x</i>@endpush")

        self.assertRegex(html, r"^<!--pb:push [0-9a-f]+--><i>x</i><!--pb:stack scripts-->$")

    def test_the_name_may_be_an_expression(self):
        html = self._render("@stack(where)@push(where)<i>x</i>@endpush", {"where": "s"})

        self.assertEqual(visible(html), "<i>x</i>")

    def test_an_unclosed_push_is_an_error(self):
        with self.assertRaises(Exception):
            self._render("@stack('s')@push('s')<i>x</i>")


class TestCollecting(ComponentTestCase):
    """What a live update is told about: the pushes of a render with no stack of its own."""

    def test_the_pushes_of_a_render_can_be_read_back(self):
        with stacks.collecting() as collector:
            html = self._render("<div>@push('scripts')<script>a</script>@endpush</div>")

        self.assertEqual(html, "<div></div>")
        self.assertEqual(collector.pushes_for_client(), [
            {"stack": "scripts", "key": stacks.key_of("<script>a</script>"), "html": "<script>a</script>"},
        ])

    def test_the_pushes_read_back_are_kept_once(self):
        with stacks.collecting() as collector:
            self._render("@push('s')<i>a</i>@endpush@push('s')<i>a</i>@endpush")

        self.assertEqual(len(collector.pushes_for_client()), 1)

    def test_nothing_is_left_behind_once_a_render_is_done(self):
        self._render("@push('s')<i>a</i>@endpush")

        with stacks.collecting() as collector:
            self._render("<p></p>")

        self.assertEqual(collector.pushes_for_client(), [])
