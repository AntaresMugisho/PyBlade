import sys
import types
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("questionary", MagicMock())

from pyblade import i18n


class TestI18nModule(unittest.TestCase):
    def test_public_wrapper_functions_exist(self):
        self.assertTrue(callable(i18n.gettext))
        self.assertTrue(callable(i18n.ngettext))
        self.assertTrue(callable(i18n.pgettext))
        self.assertTrue(callable(i18n.npgettext))

    def test_prefers_django_translation_when_available(self):
        django_translation = types.SimpleNamespace(
            gettext=lambda message: f"django:{message}",
            ngettext=lambda singular, plural, count: f"django:{singular}|{plural}|{count}",
            pgettext=lambda context, message: f"django:{context}:{message}",
            npgettext=lambda context, singular, plural, count: f"django:{context}:{singular}|{plural}|{count}",
        )
        django_module = types.ModuleType("django.utils.translation")
        django_module.gettext = django_translation.gettext
        django_module.ngettext = django_translation.ngettext
        django_module.pgettext = django_translation.pgettext
        django_module.npgettext = django_translation.npgettext

        django_utils = types.ModuleType("django.utils")
        django_utils.translation = django_module

        django_pkg = types.ModuleType("django")
        django_pkg.utils = django_utils

        with patch.dict(
            sys.modules,
            {
                "django": django_pkg,
                "django.utils": django_utils,
                "django.utils.translation": django_module,
            },
        ):
            self.assertEqual(i18n.gettext("Hello"), "django:Hello")
            self.assertEqual(i18n.pgettext("greeting", "Hello"), "django:greeting:Hello")
            self.assertEqual(i18n.ngettext("one", "many", 2), "django:one|many|2")
            self.assertEqual(i18n.npgettext("greeting", "one", "many", 2), "django:greeting:one|many|2")
