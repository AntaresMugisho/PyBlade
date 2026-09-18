"""Walking through a long list a page at a time, from inside a component.

The page a component is on is part of what it holds, so it survives every round
trip, and moving to the next one is an action like any other rather than a new
request for a new URL. What does the counting and the slicing is Django's own
paginator; what is checked here is everything around it.
"""

import unittest

from pyblade.live.base import LiveComponent
from pyblade.live.pagination import DEFAULT_PAGE_NAME, Page, Paginator


def component(**body):
    body.setdefault("render", lambda self: self.render_inline("<div>x</div>", context={}))
    return type("Listing", (LiveComponent, Paginator), body)


def things(count=95):
    return [f"thing {number}" for number in range(1, count + 1)]


class TestTheMixinBelongingToTheComponent(unittest.TestCase):
    """A mixin says its methods are the component's; without that they are not."""

    def test_its_actions_are_ones_the_page_may_call(self):
        instance = component()("pb-test")

        for action in ("next_page", "previous_page", "set_page", "reset_page"):
            self.assertIn(action, instance._get_methods())

    def test_the_page_it_is_on_is_part_of_the_state(self):
        self.assertIn("paginators", component()("pb-test")._get_state())

    def test_it_is_a_mixin_by_what_it_inherits(self):
        from pyblade.live import ComponentMixin

        self.assertTrue(issubclass(Paginator, ComponentMixin))

    def test_a_mixin_that_says_nothing_is_left_out(self):
        """A component built on some other class does not hand it to the browser."""

        class Ordinary:
            secret = "not for the page"

            def dangerous(self):
                pass

        cls = type("Listing", (LiveComponent, Ordinary), {
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })
        instance = cls("pb-test")

        self.assertNotIn("secret", instance._get_state())
        self.assertNotIn("dangerous", instance._get_methods())

    def test_each_component_walks_its_own_pages(self):
        """What a class declares is shared until a component makes it its own."""
        first, second = component()("a"), component()("b")

        first.next_page()

        self.assertEqual(first.page_of(), 2)
        self.assertEqual(second.page_of(), 1)


class TestTakingAPage(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def test_the_first_page_is_where_it_starts(self):
        page = self.component.paginate(things(), 10)

        self.assertEqual(page.current_page(), 1)
        self.assertEqual(page.items(), things()[:10])

    def test_the_page_it_is_on_is_the_one_it_takes(self):
        self.component.set_page(3)

        self.assertEqual(self.component.paginate(things(), 10).items(), things()[20:30])

    def test_what_it_answers_about_the_list(self):
        page = self.component.paginate(things(95), 10)

        self.assertEqual(page.total(), 95)
        self.assertEqual(page.last_page(), 10)
        self.assertEqual(page.per_page(), 10)
        self.assertEqual(page.count(), 10)
        self.assertEqual(page.first_item(), 1)
        self.assertEqual(page.last_item(), 10)

    def test_the_last_page_may_hold_fewer(self):
        self.component.set_page(10)
        page = self.component.paginate(things(95), 10)

        self.assertEqual(page.count(), 5)
        self.assertEqual(page.last_item(), 95)

    def test_a_page_may_be_looped_over_as_the_list_it_is(self):
        page = self.component.paginate(things(15), 10)

        self.assertEqual(list(page), things()[:10])
        self.assertEqual(len(page), 10)

    def test_where_it_stands_among_the_pages(self):
        page = self.component.paginate(things(95), 10)

        self.assertTrue(page.on_first_page())
        self.assertFalse(page.on_last_page())
        self.assertTrue(page.has_more_pages())
        self.assertTrue(page.has_pages())

    def test_a_list_that_fits_on_one_page_has_no_pages_to_walk(self):
        self.assertFalse(self.component.paginate(things(4), 10).has_pages())

    def test_a_page_that_is_no_longer_there_is_the_last_one_that_is(self):
        """The list grew shorter while the reader was looking at it."""
        self.component.set_page(9)

        page = self.component.paginate(things(12), 10)

        self.assertEqual(page.current_page(), 2)
        self.assertEqual(self.component.page_of(), 2)

    def test_an_empty_list_is_still_a_page(self):
        page = self.component.paginate([], 10)

        self.assertEqual(page.count(), 0)
        self.assertFalse(page.has_pages())


class TestMovingBetweenPages(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def test_going_on_and_going_back(self):
        self.component.next_page()
        self.component.next_page()
        self.assertEqual(self.component.page_of(), 3)

        self.component.previous_page()
        self.assertEqual(self.component.page_of(), 2)

    def test_there_is_no_page_before_the_first(self):
        self.component.previous_page()

        self.assertEqual(self.component.page_of(), 1)

    def test_going_to_a_page_outright(self):
        self.component.set_page(7)

        self.assertEqual(self.component.page_of(), 7)

    def test_starting_over(self):
        self.component.set_page(5)
        self.component.reset_page()

        self.assertEqual(self.component.page_of(), 1)

    def test_what_the_page_may_send_is_read_as_a_number_or_ignored(self):
        self.component.set_page("4")
        self.assertEqual(self.component.page_of(), 4)

        self.component.set_page("the fourth")
        self.assertEqual(self.component.page_of(), 4)


class TestSeveralPaginatorsAtOnce(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def test_each_is_on_a_page_of_its_own(self):
        self.component.set_page(3, "invoice_page")

        self.assertEqual(self.component.page_of("invoice_page"), 3)
        self.assertEqual(self.component.page_of(), 1)

    def test_they_take_their_own_pages_of_their_own_lists(self):
        self.component.set_page(2, "invoice_page")

        clients = self.component.paginate(things(50), 10)
        invoices = self.component.paginate(things(50), 10, page_name="invoice_page")

        self.assertEqual(clients.current_page(), 1)
        self.assertEqual(invoices.current_page(), 2)

    def test_the_name_travels_with_the_links(self):
        invoices = self.component.paginate(things(50), 10, page_name="invoice_page")

        self.assertEqual(invoices.get_page_name(), "invoice_page")
        self.assertIn("invoice_page=2", invoices.url(2))


class TestWatchingThePageChange(unittest.TestCase):
    def test_the_hook_named_after_the_paginator_runs(self):
        seen = []
        instance = component(updating_page=lambda self, page: seen.append(("updating", page)),
                             updated_page=lambda self, page: seen.append(("updated", page)))("pb-test")

        instance.set_page(4)

        self.assertEqual(seen, [("updating", 4), ("updated", 4)])

    def test_it_runs_before_and_after_the_page_has_changed(self):
        seen = []
        instance = component(
            updating_page=lambda self, page: seen.append(self.page_of()),
            updated_page=lambda self, page: seen.append(self.page_of()),
        )("pb-test")

        instance.set_page(4)

        self.assertEqual(seen, [1, 4])

    def test_a_named_paginator_has_a_hook_of_its_own(self):
        seen = []
        instance = component(updating_invoice_page=lambda self, page: seen.append(page))("pb-test")

        instance.set_page(2, "invoice_page")
        instance.set_page(9)

        self.assertEqual(seen, [2])

    def test_a_hook_may_watch_any_of_them(self):
        seen = []
        instance = component(
            updating_paginators=lambda self, page, page_name: seen.append((page_name, page))
        )("pb-test")

        instance.set_page(2)
        instance.set_page(3, "invoice_page")

        self.assertEqual(seen, [("page", 2), ("invoice_page", 3)])


class TestWhatTheLinksSay(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def _page(self, count=400, per_page=10, on=1):
        self.component.set_page(on)
        return self.component.paginate(things(count), per_page)

    def test_a_short_list_shows_every_page(self):
        self.assertEqual(self._page(count=50).window(), [1, 2, 3, 4, 5])

    def test_a_long_list_shows_the_ones_nearby(self):
        window = self._page(on=20).window(on_each_side=2)

        self.assertEqual(window, [1, None, 18, 19, 20, 21, 22, None, 40])

    def test_the_first_and_last_are_always_there(self):
        window = self._page(on=20).window()

        self.assertEqual(window[0], 1)
        self.assertEqual(window[-1], 40)

    def test_a_gap_is_written_where_the_numbers_skip(self):
        self.assertIn(None, self._page(on=20).window())

    def test_no_gap_on_the_side_where_there_is_nothing_to_skip(self):
        """Near the start the numbers run on from the first, with a gap only after."""
        window = self._page(on=2).window(on_each_side=5)

        self.assertEqual(window[:4], [1, 2, 3, 4])
        self.assertIsNone(window[-2])

    def test_how_many_are_shown_may_be_said(self):
        self.assertEqual(len(self._page(on=20).window(on_each_side=1)), 7)


class TestWhereTheLinksPoint(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def test_a_link_names_the_page_it_goes_to(self):
        page = self.component.paginate(things(), 10)

        self.assertIn("page=3", page.url(3))

    def test_the_path_may_be_said(self):
        page = self.component.paginate(things(), 10).with_path("/admin/users")

        self.assertEqual(page.url(2), "/admin/users?page=2")

    def test_something_else_may_be_carried_along(self):
        page = self.component.paginate(things(), 10).appends(sort="votes")

        self.assertIn("sort=votes", page.url(2))
        self.assertIn("page=2", page.url(2))

    def test_the_address_bar_may_be_left_out_of_it(self):
        page = self.component.paginate(things(), 10)
        self.assertTrue(page.query_string)

        page.without_query_string()

        self.assertFalse(page.query_string)

    def test_what_it_was_asked_for_can_be_read_back(self):
        page = self.component.paginate(things(), 10, page_name="invoice_page").appends(sort="votes")

        options = page.get_options()

        self.assertEqual(options["page_name"], "invoice_page")
        self.assertEqual(options["appends"], {"sort": "votes"})


class TestDrawingTheLinks(unittest.TestCase):
    def setUp(self):
        self.component = component()("pb-test")

    def test_the_links_are_markup_rather_than_text(self):
        from pyblade.engine.contexts import SafeContent

        page = self.component.paginate(things(50), 10)

        self.assertIsInstance(page.links, SafeContent)

    def test_they_draw_the_buttons_that_walk_the_pages(self):
        markup = str(self.component.paginate(things(50), 10).links)

        self.assertIn('pb:click="next_page"', markup)
        self.assertIn("Next", markup)

    def test_a_list_that_fits_on_one_page_draws_nothing(self):
        self.assertEqual(str(self.component.paginate(things(4), 10).links).strip(), "")

    def test_the_page_it_is_on_is_marked_as_the_one_it_is(self):
        self.component.set_page(2)
        markup = str(self.component.paginate(things(50), 10).links)

        self.assertIn('aria-current="page"', markup)

    def test_there_is_nothing_to_go_back_to_from_the_first_page(self):
        markup = str(self.component.paginate(things(50), 10).links)

        self.assertNotIn('pb:click="previous_page"', markup)

    def test_asking_for_them_differently_says_the_same_thing(self):
        page = self.component.paginate(things(50), 10)

        self.assertEqual(str(page.links), str(page.links()))

    def test_how_many_numbers_to_show_may_be_asked_for(self):
        self.component.set_page(20)
        page = self.component.paginate(things(400), 10)

        self.assertLess(len(str(page.links(on_each_side=1))), len(str(page.links(on_each_side=5))))


class TestWhatTheAddressBarIsTold(unittest.TestCase):
    """The page being looked at shows in the address bar, unless it is told not to."""

    def _rendered(self, **body):
        body.setdefault("render", lambda self: str(self.paginate(things(50), 10).links))
        instance = component(**body)("pb-test")
        instance.render()
        return instance

    def test_the_page_being_looked_at_is_said(self):
        instance = self._rendered()
        instance.set_page(3)
        instance.render()

        self.assertEqual(instance.pagination_query(), {"page": 3})

    def test_a_named_paginator_is_said_by_its_name(self):
        instance = self._rendered(
            render=lambda self: str(self.paginate(things(50), 10, page_name="invoice_page").links)
        )

        self.assertEqual(instance.pagination_query(), {"invoice_page": 1})

    def test_what_is_carried_along_is_said_too(self):
        instance = self._rendered(
            render=lambda self: str(self.paginate(things(50), 10).appends(sort="votes").links)
        )

        self.assertEqual(instance.pagination_query(), {"page": 1, "sort": "votes"})

    def test_a_paginator_may_ask_to_be_left_out_of_it(self):
        instance = self._rendered(
            render=lambda self: str(self.paginate(things(50), 10).without_query_string().links)
        )

        self.assertEqual(instance.pagination_query(), {})

    def test_a_component_rendered_twice_says_it_once(self):
        instance = self._rendered()
        instance.render()

        self.assertEqual(instance.pagination_query(), {"page": 1})

    def test_a_component_that_does_not_paginate_says_nothing(self):
        plain = type("Plain", (LiveComponent,), {
            "render": lambda self: self.render_inline("<div>x</div>", context={}),
        })

        result = plain.update_component({"_id": "pb-test"}, "$refresh")

        self.assertNotIn("query", result)

    def test_the_answer_carries_it_to_the_page(self):
        cls = component(render=lambda self: str(self.paginate(things(50), 10).links))

        result = cls.update_component({"_id": "pb-test"}, "next_page")

        self.assertEqual(result["query"], {"page": 2})
        self.assertIs(result["scroll"], True)

    def test_where_to_scroll_may_be_said(self):
        instance = self._rendered(
            render=lambda self: str(self.paginate(things(50), 10).links(scroll_to="#posts"))
        )

        self.assertEqual(instance.pagination_scroll(), "#posts")

    def test_scrolling_may_be_turned_off(self):
        instance = self._rendered(
            render=lambda self: str(self.paginate(things(50), 10).links(scroll_to=False))
        )

        self.assertIs(instance.pagination_scroll(), False)


class TestComingBackToThePageTheAddressBarNames(unittest.TestCase):
    """A link someone was sent, or a page reloaded, comes back where it was."""

    def _component(self, query=None):
        instance = component()("pb-test")
        instance._request = type("Request", (), {"GET": query or {}, "path": "/posts"})()
        return instance

    def test_the_page_named_in_the_address_bar_is_the_one_shown(self):
        instance = self._component({"page": "4"})

        self.assertEqual(instance.paginate(things(200), 10).current_page(), 4)

    def test_the_component_holds_it_from_then_on(self):
        instance = self._component({"page": "4"})
        instance.paginate(things(200), 10)

        self.assertEqual(instance.page_of(), 4)

    def test_a_named_paginator_is_read_by_its_own_name(self):
        instance = self._component({"invoice_page": "3"})

        page = instance.paginate(things(200), 10, page_name="invoice_page")

        self.assertEqual(page.current_page(), 3)

    def test_nothing_in_the_address_bar_is_the_first_page(self):
        self.assertEqual(self._component().paginate(things(200), 10).current_page(), 1)

    def test_nonsense_in_the_address_bar_is_the_first_page(self):
        instance = self._component({"page": "the fourth"})

        self.assertEqual(instance.paginate(things(200), 10).current_page(), 1)

    def test_the_address_bar_is_read_only_while_the_page_is_being_built(self):
        """Once it is running, the component knows which page it is on."""
        instance = self._component({"page": "4"})
        instance._rerendering = True
        instance.set_page(2)

        self.assertEqual(instance.paginate(things(200), 10).current_page(), 2)
