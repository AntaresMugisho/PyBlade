"""@lang and @languages: which language the page is in, and which it could be.

@lang                          fr
@lang(as CURRENT_LANGUAGE)     stored, nothing written
@languages                     stored as `languages`, nothing written
@languages(as LANGUAGES)       stored under the name given
"""

import unittest
from contextlib import ExitStack

from django.test import override_settings
from django.utils import translation

from pyblade.config import config
from pyblade.engine.processor import TemplateProcessor


class LanguagesTestCase(unittest.TestCase):
    framework = None

    def setUp(self):
        self._stack = ExitStack()
        self.addCleanup(self._stack.close)
        self.override({"stack.framework": self.framework or ""})

    def override(self, values):
        """Say something different about the project, for the length of the test."""
        self._stack.enter_context(config.override(values))

    def _render(self, template, context=None):
        return TemplateProcessor().render(template, context or {})


class TestWithDjango(LanguagesTestCase):
    framework = "django"

    def test_lang_writes_the_language_the_page_is_in(self):
        with override_settings(USE_I18N=True), translation.override("fr"):
            self.assertEqual(self._render('<html lang="@lang">'), '<html lang="fr">')

    def test_lang_as_stores_it_and_writes_nothing(self):
        with override_settings(USE_I18N=True), translation.override("fr"):
            html = self._render("@lang(as CURRENT_LANGUAGE)[{{ CURRENT_LANGUAGE }}]")

        self.assertEqual(html, "[fr]")

    def test_languages_are_the_ones_the_project_offers(self):
        with override_settings(LANGUAGES=[("en", "English"), ("fr", "French")]):
            html = self._render(
                "@languages(as LANGUAGES)@for(language in LANGUAGES){{ language[0] }}={{ language[1] }};@endfor"
            )

        self.assertEqual(html, "en=English;fr=French;")

    def test_languages_without_a_name_are_stored_as_languages(self):
        with override_settings(LANGUAGES=[("en", "English")]):
            html = self._render("@languages[{{ languages[0][0] }}]")

        self.assertEqual(html, "[en]")


class TestWithoutAFramework(LanguagesTestCase):
    def test_lang_is_the_locale_pyblade_is_configured_with(self):
        self.override({"i18n.locale": "sw"})

        self.assertEqual(self._render("@lang"), "sw")

    def test_languages_are_read_from_the_configuration(self):
        self.override({"i18n.languages": [["en", "English"], ["sw", "Kiswahili"]]})

        html = self._render("@languages@for(language in languages){{ language[0] }}:{{ language[1] }} @endfor")

        self.assertEqual(html, "en:English sw:Kiswahili ")

    def test_languages_are_none_when_the_configuration_names_none(self):
        self.override({"i18n.languages": []})

        self.assertEqual(self._render("@languages{{ len(languages) }}"), "0")


if __name__ == "__main__":
    unittest.main()
