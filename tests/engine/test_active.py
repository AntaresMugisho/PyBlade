"""@active: what to show when the reader is on a particular page.

A navigation menu wants to mark where the reader is, and a page often wants to
say something only while it is the page being looked at. Both come down to the
same question -- is this where we are? -- so it is asked the way every other
question is asked in a template, with a block that renders what is inside it
when the answer is yes.

Where we are is said either by the name of the route, as Django resolves it, or
by the path itself. Either may be written with a `*` where anything will do,
which is what a parent in a menu needs: it stays lit for every page beneath it.
"""

import unittest

from pyblade.engine.processor import TemplateProcessor


class Resolved:
    """What Django leaves on a request once it knows which route was matched."""

    def __init__(self, url_name=None, view_name=None, namespace=""):
        self.url_name = url_name
        self.view_name = view_name or url_name
        self.namespace = namespace


class Request:
    """Enough of a request for a template to ask where the reader is."""

    def __init__(self, path="/", url_name=None, view_name=None):
        self.path = path
        self.resolver_match = Resolved(url_name, view_name) if url_name or view_name else None


class ActiveTestCase(unittest.TestCase):
    def setUp(self):
        self.processor = TemplateProcessor()

    def render(self, template, request=None, **context):
        return self.processor.render(template, {"request": request, **context}).strip()


class TestByRouteName(ActiveTestCase):
    def test_the_body_is_rendered_on_the_page_it_names(self):
        template = "@active('dashboard')You are here@endactive"

        self.assertEqual(self.render(template, Request("/dash/", "dashboard")), "You are here")

    def test_and_not_on_any_other(self):
        template = "@active('dashboard')You are here@endactive"

        self.assertEqual(self.render(template, Request("/profile/", "profile")), "")

    def test_a_namespaced_route_is_matched_by_its_whole_name(self):
        template = "@active('blog:index')Blog@endactive"
        request = Request("/blog/", url_name="index", view_name="blog:index")

        self.assertEqual(self.render(template, request), "Blog")

    def test_a_namespaced_route_is_matched_by_its_short_name_too(self):
        template = "@active('index')Blog@endactive"
        request = Request("/blog/", url_name="index", view_name="blog:index")

        self.assertEqual(self.render(template, request), "Blog")

    def test_a_star_stands_for_anything(self):
        template = "@active('blog:*')Blog@endactive"
        request = Request("/blog/3/", url_name="detail", view_name="blog:detail")

        self.assertEqual(self.render(template, request), "Blog")

    def test_a_star_does_not_reach_another_namespace(self):
        template = "@active('blog:*')Blog@endactive"
        request = Request("/shop/3/", url_name="detail", view_name="shop:detail")

        self.assertEqual(self.render(template, request), "")


class TestByPath(ActiveTestCase):
    def test_a_path_is_matched_as_it_is_written(self):
        template = "@active('/posts/')Posts@endactive"

        self.assertEqual(self.render(template, Request("/posts/")), "Posts")

    def test_a_path_that_is_not_the_one_we_are_on(self):
        template = "@active('/posts/')Posts@endactive"

        self.assertEqual(self.render(template, Request("/pages/")), "")

    def test_a_star_covers_everything_below_it(self):
        """What a parent in a menu needs: lit for every page beneath it."""
        template = "@active('/posts/*')Posts@endactive"

        self.assertEqual(self.render(template, Request("/posts/3/edit/")), "Posts")

    def test_the_page_the_star_hangs_off_is_covered_too(self):
        template = "@active('/posts/*')Posts@endactive"

        self.assertEqual(self.render(template, Request("/posts/")), "Posts")

    def test_a_star_stops_where_the_path_stops_matching(self):
        template = "@active('/posts/*')Posts@endactive"

        self.assertEqual(self.render(template, Request("/pages/3/")), "")

    def test_a_path_is_told_from_a_route_name_by_the_slash(self):
        """'/dashboard' asks about the path; 'dashboard' asks about the route."""
        template = "@active('/dashboard')Here@endactive"
        request = Request("/somewhere/else/", url_name="dashboard")

        self.assertEqual(self.render(template, request), "")


class TestSeveralAtOnce(ActiveTestCase):
    def test_any_of_them_being_where_we_are_is_enough(self):
        template = "@active('posts', '/archive/*')Writing@endactive"

        self.assertEqual(self.render(template, Request("/archive/2024/")), "Writing")
        self.assertEqual(self.render(template, Request("/p/", "posts")), "Writing")
        self.assertEqual(self.render(template, Request("/about/", "about")), "")


class TestWhenWeAreElsewhere(ActiveTestCase):
    def test_what_to_show_instead_may_be_said(self):
        template = "@active('dashboard')Here@else Elsewhere @endactive"

        self.assertEqual(self.render(template, Request("/other/", "other")), "Elsewhere")

    def test_and_is_not_shown_when_we_are_here(self):
        template = "@active('dashboard')Here@else Elsewhere @endactive"

        self.assertEqual(self.render(template, Request("/dash/", "dashboard")), "Here")

    def test_a_template_rendered_with_no_request_is_nowhere(self):
        """Nothing is being served, so nothing is the page being looked at."""
        template = "@active('dashboard')Here@else Elsewhere @endactive"

        self.assertEqual(self.render(template, None), "Elsewhere")

    def test_a_request_that_matched_no_route_can_still_be_asked_about_its_path(self):
        template = "@active('/posts/*')Posts@endactive"

        self.assertEqual(self.render(template, Request("/posts/3/")), "Posts")


class TestWhatIsInside(ActiveTestCase):
    def test_the_body_is_a_template_like_any_other(self):
        template = "@active('dashboard')<b>{{ name }}</b>@endactive"
        request = Request("/dash/", "dashboard")

        self.assertEqual(self.render(template, request, name="Antares"), "<b>Antares</b>")

    def test_a_directive_may_be_written_inside_it(self):
        template = "@active('dashboard')@if(True)yes@endif@endactive"

        self.assertEqual(self.render(template, Request("/dash/", "dashboard")), "yes")

    def test_it_may_be_written_inside_another_directive(self):
        template = "@if(True)@active('dashboard')Here@endactive@endif"

        self.assertEqual(self.render(template, Request("/dash/", "dashboard")), "Here")

    def test_it_marks_the_item_of_a_menu_it_wraps(self):
        """The case it is for: a class on the element around the link."""
        template = "<li class=\"@active('dashboard')is-active@endactive\">Dashboard</li>"

        self.assertEqual(
            self.render(template, Request("/dash/", "dashboard")),
            '<li class="is-active">Dashboard</li>',
        )
