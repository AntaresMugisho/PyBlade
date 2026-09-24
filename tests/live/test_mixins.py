"""Behaviour a component takes from somewhere other than LiveComponent.

A mixin that inherits ComponentMixin brings what it declares into the component
that mixes it in: its methods become actions the page may call, and what it
holds becomes state. A class that does not inherit it brings nothing, however
it got into the component's bases -- a component built on a class of the project
does not hand that class to the browser.
"""

import unittest

from pyblade.live import ComponentMixin, LiveComponent, Paginator


def render(self):
    return self.render_inline("<div>x</div>", context={})


class Sortable(ComponentMixin):
    """A mixin as a project writes one."""

    sort = "name"
    ascending = True

    def sort_by(self, column):
        self.sort = column

    def _secret(self):
        """Private, so not an action however it was brought in."""


class Ordinary:
    """A class of the project that says nothing about components."""

    note = "not for the page"

    def dangerous(self):
        pass


def component(*bases, **body):
    body.setdefault("render", render)
    return type("Listing", (LiveComponent, *bases), body)


class TestWhatAMixinBrings(unittest.TestCase):
    def test_its_methods_are_actions_the_page_may_call(self):
        self.assertIn("sort_by", component(Sortable)("pb-test")._get_methods())

    def test_what_it_holds_is_state(self):
        state = component(Sortable)("pb-test")._get_state()

        self.assertEqual((state["sort"], state["ascending"]), ("name", True))

    def test_what_it_keeps_private_stays_private(self):
        self.assertNotIn("_secret", component(Sortable)("pb-test")._get_methods())

    def test_an_action_of_the_mixin_is_called_like_any_other(self):
        result = component(Sortable).update_component({"_id": "pb-test"}, "sort_by", ["date"])

        self.assertEqual(result["snapshot"]["state"]["sort"], "date")

    def test_what_it_holds_is_what_reset_takes_the_component_back_to(self):
        instance = component(Sortable)("pb-test")
        instance.sort = "date"

        instance.reset("sort")

        self.assertEqual(instance.sort, "name")


class TestWhatAnythingElseBrings(unittest.TestCase):
    """Nothing, whatever it declares."""

    def test_its_methods_are_not_actions(self):
        self.assertNotIn("dangerous", component(Ordinary)("pb-test")._get_methods())

    def test_what_it_holds_is_not_state(self):
        self.assertNotIn("note", component(Ordinary)("pb-test")._get_state())

    def test_nor_can_the_page_call_them(self):
        with self.assertRaises((AttributeError, NameError)):
            component(Ordinary).update_component({"_id": "pb-test"}, "dangerous")

    def test_a_class_a_mixin_is_built_on_brings_nothing_either(self):
        """Only the classes that say they are mixins count, not what is below them."""

        class Built(Ordinary, ComponentMixin):
            flag = True

        instance = component(Built)("pb-test")

        self.assertIn("flag", instance._get_state())
        self.assertNotIn("note", instance._get_state())
        self.assertNotIn("dangerous", instance._get_methods())


class TestMixinsTogether(unittest.TestCase):
    def test_a_mixin_may_be_built_on_another(self):
        class Filterable(Sortable):
            query = ""

            def search(self):
                pass

        instance = component(Filterable)("pb-test")

        self.assertIn("sort_by", instance._get_methods())
        self.assertIn("search", instance._get_methods())
        self.assertIn("query", instance._get_state())

    def test_several_may_be_mixed_in_at_once(self):
        instance = component(Sortable, Paginator)("pb-test")

        self.assertIn("sort_by", instance._get_methods())
        self.assertIn("next_page", instance._get_methods())

    def test_what_the_component_declares_wins_over_what_it_mixes_in(self):
        instance = component(Sortable, sort="date")("pb-test")

        self.assertEqual(instance._get_state()["sort"], "date")


class TestTheMixinItself(unittest.TestCase):
    def test_it_brings_nothing_of_its_own(self):
        """Inheriting it is a statement, not a set of names in the component."""
        bare = component()("pb-test")
        mixed = component(ComponentMixin)("pb-test")

        self.assertEqual(bare._get_state(), mixed._get_state())
        self.assertEqual(set(bare._get_methods()), set(mixed._get_methods()))

    def test_it_asks_nothing_of_the_classes_built_on_it(self):
        """No constructor, so no mixin is drawn into cooperating with one."""
        self.assertNotIn("__init__", vars(ComponentMixin))

    def test_it_owes_nothing_to_any_framework(self):
        """What a component is made of is the same whatever serves it."""
        import ast
        import inspect

        import pyblade.live.mixins as module

        tree = ast.parse(inspect.getsource(module))
        imported = [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names] + [
            node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ]

        self.assertEqual(imported, [])

    def test_the_paginator_is_one(self):
        self.assertTrue(issubclass(Paginator, ComponentMixin))
