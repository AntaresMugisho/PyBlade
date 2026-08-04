"""@field and @error, against real Django forms."""

import unittest

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        USE_I18N=False,
        INSTALLED_APPS=["django.forms"],
        STATIC_URL="/static/",
        MEDIA_URL="/media/",
    )
    django.setup()

from django import forms  # noqa: E402

from pyblade.engine.processor import TemplateProcessor  # noqa: E402


class ContactForm(forms.Form):
    name = forms.CharField(max_length=50)
    email = forms.EmailField()


class StyledForm(forms.Form):
    name = forms.CharField(widget=forms.TextInput(attrs={"class": "default"}))


class FormTestCase(unittest.TestCase):
    def setUp(self):
        self.processor = TemplateProcessor()

    def _render(self, template, context=None):
        return self.processor.render(template, context or {})

    def _invalid_form(self):
        form = ContactForm(data={"name": "", "email": "not-an-email"})
        form.is_valid()
        return form


class TestFieldAccess(FormTestCase):
    def test_a_form_field_is_reachable_as_an_attribute(self):
        form = ContactForm()

        self.assertEqual(self._render("{!! form.name !!}", {"form": form}), str(form["name"]))


class TestFieldDirective(FormTestCase):
    def test_field_renders_the_widget(self):
        form = ContactForm()

        self.assertEqual(self._render("@field(form.name)", {"form": form}), str(form["name"]))

    def test_field_adds_the_attributes_it_is_given(self):
        template = '@field(form.name, class="form-control" placeholder="Enter your name")'

        result = self._render(template, {"form": ContactForm()})

        self.assertIn('class="form-control"', result)
        self.assertIn('placeholder="Enter your name"', result)

    def test_attribute_without_a_value_is_rendered_bare(self):
        result = self._render("@field(form.name, autofocus)", {"form": ContactForm()})

        self.assertIn(" autofocus", result)
        self.assertNotIn('autofocus="', result)

    def test_attributes_may_be_separated_by_commas(self):
        template = '@field(form.name, class="form-control", placeholder="Enter your name")'

        result = self._render(template, {"form": ContactForm()})

        self.assertIn('class="form-control"', result)
        self.assertIn('placeholder="Enter your name"', result)

    def test_unquoted_attribute_value_is_an_expression(self):
        template = "@field(form.name, placeholder=label)"

        result = self._render(template, {"form": ContactForm(), "label": "From the context"})

        self.assertIn('placeholder="From the context"', result)

    def test_attribute_replaces_the_one_the_widget_carries(self):
        result = self._render('@field(form.name, class="replaced")', {"form": StyledForm()})

        self.assertIn('class="replaced"', result)
        self.assertNotIn("default", result)

    def test_attribute_can_be_appended_to_the_one_the_widget_carries(self):
        result = self._render('@field(form.name, class+="extra")', {"form": StyledForm()})

        self.assertIn('class="default extra"', result)

    def test_field_of_an_invalid_form_still_renders(self):
        result = self._render('@field(form.email, class="form-control")', {"form": self._invalid_form()})

        self.assertIn('class="form-control"', result)
        self.assertIn('name="email"', result)


class TestErrorDirective(FormTestCase):
    TEMPLATE = '@error(form.email)<small style="color:red;">{{ message }}</small>@enderror'

    def test_error_renders_its_body_with_the_message(self):
        result = self._render(self.TEMPLATE, {"form": self._invalid_form()})

        self.assertEqual(result, '<small style="color:red;">Enter a valid email address.</small>')

    def test_error_renders_nothing_when_the_field_is_valid(self):
        form = ContactForm(data={"name": "Antares", "email": "hi@example.com"})
        form.is_valid()

        self.assertEqual(self._render(self.TEMPLATE, {"form": form}), "")

    def test_error_renders_nothing_on_an_unbound_form(self):
        self.assertEqual(self._render(self.TEMPLATE, {"form": ContactForm()}), "")

    def test_every_message_of_the_field_is_available(self):
        template = "@error(form.email)@for(error in messages){{ error }}@endfor@enderror"

        result = self._render(template, {"form": self._invalid_form()})

        self.assertEqual(result, "Enter a valid email address.")

    def test_the_whole_form_renders(self):
        template = (
            "<form>@csrf"
            '<div>@field(form.name, class="form-control" placeholder="Enter your name" required)'
            '@error(form.name)<small style="color:red;">{{ message }}</small>@enderror</div>'
            '<div>@field(form.email, class="form-control")'
            '@error(form.email)<small style="color:red;">{{ message }}</small>@enderror</div>'
            "</form>"
        )

        result = self._render(template, {"form": self._invalid_form(), "csrf_token": "token"})

        self.assertIn('name="csrfmiddlewaretoken" value="token"', result)
        self.assertEqual(result.count('class="form-control"'), 2)
        self.assertIn('<small style="color:red;">This field is required.</small>', result)
        self.assertIn('<small style="color:red;">Enter a valid email address.</small>', result)


if __name__ == "__main__":
    unittest.main()