"""Checking what a component holds before acting on it.

A component says what its properties must look like, and PyBlade checks them
against that before an action runs. What does the checking is a Django form --
the one the component points at, or one assembled from the fields it declares --
so every field, validator and message Django ships works here, translations and
all, and nothing new had to be invented to say "this must be an email address".
"""

import unittest

from django import forms

from pyblade.live.base import LiveComponent
from pyblade.live.decorators import validate


def component(**body):
    body.setdefault("render", lambda self: self.render_inline("<div>{{ email }}</div>", context={}))
    body.setdefault("email", "")
    return type("Signup", (LiveComponent,), body)


class ContactForm(forms.Form):
    email = forms.EmailField()
    age = forms.IntegerField(min_value=18)


class TestSayingWhatIsExpected(unittest.TestCase):
    """Either point at a form, or declare the fields where the properties are."""

    def test_a_component_may_point_at_a_form(self):
        cls = component(form_class=ContactForm, age=0)

        self.assertIs(cls._validation_form(), ContactForm)

    def test_a_component_may_declare_its_fields_instead(self):
        cls = component(rules={"email": forms.EmailField()})

        self.assertIn("email", cls._validation_form().base_fields)

    def test_what_is_declared_is_assembled_once(self):
        cls = component(rules={"email": forms.EmailField()})

        self.assertIs(cls._validation_form(), cls._validation_form())

    def test_a_component_expecting_nothing_has_no_form(self):
        self.assertIsNone(component()._validation_form())

    def test_what_is_expected_is_not_part_of_the_state(self):
        cls = component(rules={"email": forms.EmailField()}, form_class=None)

        state = cls("pb-test")._get_state()

        self.assertNotIn("rules", state)
        self.assertNotIn("form_class", state)
        self.assertNotIn("errors", state)


class TestChecking(unittest.TestCase):
    def _component(self, **body):
        body.setdefault(
            "rules",
            {"email": forms.EmailField(), "age": forms.IntegerField(min_value=18)},
        )
        body.setdefault("age", 20)
        return component(**body)("pb-test")

    def test_what_is_right_passes(self):
        instance = self._component(email="hi@example.com")

        self.assertIs(instance.validate(), True)
        self.assertEqual(instance.errors, {})

    def test_what_is_wrong_does_not(self):
        instance = self._component(email="not an email")

        self.assertIs(instance.validate(), False)

    def test_what_was_wrong_with_it_is_said(self):
        instance = self._component(email="not an email")
        instance.validate()

        self.assertIn("email", instance.errors)
        self.assertIn("valid email", instance.errors["email"][0])

    def test_every_field_is_checked_not_only_the_first(self):
        instance = self._component(email="not an email", age=12)
        instance.validate()

        self.assertEqual(set(instance.errors), {"email", "age"})

    def test_a_property_with_nothing_expected_of_it_is_left_alone(self):
        instance = self._component(email="hi@example.com", nickname="whatever")

        self.assertIs(instance.validate(), True)
        self.assertEqual(instance.nickname, "whatever")

    def test_a_component_expecting_nothing_is_always_right(self):
        self.assertIs(component()("pb-test").validate(), True)

    def test_what_was_checked_is_written_back_as_what_it_is(self):
        """A form turns what a page sends into what the property should hold."""
        instance = self._component(email="hi@example.com", age="42")
        instance.validate()

        self.assertEqual(instance.age, 42)
        self.assertIsInstance(instance.age, int)

    def test_a_form_of_its_own_is_used_the_same_way(self):
        instance = component(form_class=ContactForm, age=20, email="nope")("pb-test")

        self.assertIs(instance.validate(), False)
        self.assertIn("email", instance.errors)


class TestCheckingOneFieldAtATime(unittest.TestCase):
    """What a field being left behind asks for, rather than the whole form."""

    def _component(self, **body):
        body.setdefault(
            "rules",
            {"email": forms.EmailField(), "age": forms.IntegerField(min_value=18)},
        )
        return component(**body)("pb-test")

    def test_only_the_field_asked_about_is_answered_for(self):
        instance = self._component(email="not an email", age=12)

        instance.validate_only("email")

        self.assertEqual(set(instance.errors), {"email"})

    def test_a_field_that_is_right_leaves_nothing_behind(self):
        instance = self._component(email="hi@example.com", age=12)

        self.assertIs(instance.validate_only("email"), True)
        self.assertEqual(instance.errors, {})

    def test_what_was_wrong_with_another_field_is_not_forgotten(self):
        """Checking one field is not a reason to drop what was said about another."""
        instance = self._component(email="not an email", age=12)
        instance.validate()

        instance.validate_only("age")

        self.assertIn("email", instance.errors)

    def test_a_field_put_right_has_its_message_taken_away(self):
        instance = self._component(email="not an email", age=20)
        instance.validate()

        instance.email = "hi@example.com"
        instance.validate_only("email")

        self.assertEqual(instance.errors, {})

    def test_a_field_nothing_is_expected_of_is_right_by_default(self):
        instance = self._component(email="x@y.co")

        self.assertIs(instance.validate_only("nickname"), True)


class TestTheDecorator(unittest.TestCase):
    """@validate: check first, and do not run the action if it does not hold."""

    def _run(self, cls, action="save", state=None):
        return cls.update_component({"_id": "pb-test", **(state or {})}, action)

    def test_an_action_runs_when_everything_is_right(self):
        def save(self):
            self.saved = True

        cls = component(rules={"email": forms.EmailField()}, saved=False, save=validate(save))

        result = self._run(cls, state={"email": "hi@example.com"})

        self.assertIs(result["snapshot"]["state"]["saved"], True)

    def test_an_action_does_not_run_when_it_is_not(self):
        def save(self):
            self.saved = True

        cls = component(rules={"email": forms.EmailField()}, saved=False, save=validate(save))

        result = self._run(cls, state={"email": "nope"})

        self.assertIs(result["snapshot"]["state"]["saved"], False)

    def test_what_was_wrong_reaches_the_client(self):
        cls = component(rules={"email": forms.EmailField()}, save=validate(lambda self: None))

        result = self._run(cls, state={"email": "nope"})

        self.assertIn("email", result["errors"])

    def test_the_component_is_rendered_again_so_the_page_can_say_so(self):
        cls = component(rules={"email": forms.EmailField()}, save=validate(lambda self: None))

        result = self._run(cls, state={"email": "nope"})

        self.assertIsNotNone(result["html"])

    def test_an_action_without_the_decorator_runs_regardless(self):
        def save(self):
            self.saved = True

        cls = component(rules={"email": forms.EmailField()}, saved=False, save=save)

        result = self._run(cls, state={"email": "nope"})

        self.assertIs(result["snapshot"]["state"]["saved"], True)


class TestWhatTheClientIsToldAndMayNotSay(unittest.TestCase):
    def test_the_errors_travel_with_the_snapshot(self):
        instance = component(rules={"email": forms.EmailField()}, email="nope")("pb-test")
        instance.validate()

        self.assertIn("email", instance.serialize()["errors"])

    def test_they_are_signed_with_the_rest_of_it(self):
        from pyblade.live.security import verify_snapshot

        instance = component(rules={"email": forms.EmailField()}, email="nope")("pb-test")
        instance.validate()
        snapshot = instance.serialize()
        snapshot["errors"]["email"] = ["Anything at all"]

        with self.assertRaises(ValueError):
            verify_snapshot(snapshot)

    def test_they_come_back_on_the_next_request(self):
        """A field put right is not a reason to forget what another one said."""
        cls = component(rules={"email": forms.EmailField()}, bump=lambda self: None)

        result = cls.update_component(
            {"_id": "pb-test", "email": "nope"},
            "bump",
            errors={"email": ["Enter a valid email address."]},
        )

        self.assertIn("email", result["errors"])

    def test_the_client_may_not_put_words_in_the_page(self):
        cls = component(rules={"email": forms.EmailField()})

        with self.assertRaises(AttributeError):
            cls.update_component({"_id": "pb-test"}, "$set", ["errors", {"email": ["Ha"]}])
