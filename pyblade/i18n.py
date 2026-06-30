"""Minimal translation helpers for PyBlade templates."""

import gettext as _gettext
import locale as _locale
import os
from importlib import import_module

from pyblade.config import settings

__all__ = ["gettext", "ngettext", "pgettext", "npgettext", "pggetext"]

_BUILTIN_TRANSLATIONS = None


def _get_default_locale() -> str:

    # Use django default locale if available
    if settings.framework == "django":
        try:
            from django.utils.translation import get_language
            return get_language()
        except Exception:
            pass
    
    # Fallback to the default locale from settings or environment variable
    value = getattr(settings, "default_locale", None)
    if value:
        return str(value)

    return os.getenv("PYBLADE_DEFAULT_LOCALE", _locale.getdefaultlocale()[0] or "en")


def _get_builtin_translations():
    global _BUILTIN_TRANSLATIONS

    if _BUILTIN_TRANSLATIONS is None:
        domain = os.getenv("PYBLADE_TRANSLATION_DOMAIN", settings.translation_domain or "pyblade")
        localedir = os.getenv("PYBLADE_LOCALE_DIR", settings.locale_dir or "locale")
        locale = _get_default_locale()

        try:
            _BUILTIN_TRANSLATIONS = _gettext.translation(
                domain,
                localedir=localedir,
                languages=[locale],
                fallback=True,
            )
        except Exception:
            _BUILTIN_TRANSLATIONS = _gettext.NullTranslations()

    return _BUILTIN_TRANSLATIONS


def _get_django_translation():
    try:
        return import_module("django.utils.translation")
    except Exception:
        return None


def _get_flask_babel_translation():
    try:
        from flask import current_app, has_app_context
    except Exception:
        return None

    if not has_app_context():
        return None

    try:
        app = current_app._get_current_object()
    except Exception:
        return None

    if not app or "babel" not in getattr(app, "extensions", {}):
        return None

    try:
        return import_module("flask_babel")
    except Exception:
        return None


def gettext(message: str) -> str:
    django = _get_django_translation()
    if django is not None and hasattr(django, "gettext"):
        return django.gettext(message)

    flask_babel = _get_flask_babel_translation()
    if flask_babel is not None and hasattr(flask_babel, "gettext"):
        return flask_babel.gettext(message)

    return _get_builtin_translations().gettext(message)


def ngettext(singular: str, plural: str, count: int) -> str:
    django = _get_django_translation()
    if django is not None and hasattr(django, "ngettext"):
        return django.ngettext(singular, plural, count)

    flask_babel = _get_flask_babel_translation()
    if flask_babel is not None and hasattr(flask_babel, "ngettext"):
        return flask_babel.ngettext(singular, plural, count)

    return _get_builtin_translations().ngettext(singular, plural, count)


def pgettext(context: str, message: str) -> str:
    django = _get_django_translation()
    if django is not None and hasattr(django, "pgettext"):
        return django.pgettext(context, message)

    flask_babel = _get_flask_babel_translation()
    if flask_babel is not None and hasattr(flask_babel, "pgettext"):
        return flask_babel.pgettext(context, message)

    translations = _get_builtin_translations()
    if hasattr(translations, "pgettext"):
        return translations.pgettext(context, message)

    return translations.gettext(message)


def npgettext(context: str, singular: str, plural: str, count: int) -> str:
    django = _get_django_translation()
    if django is not None and hasattr(django, "npgettext"):
        return django.npgettext(context, singular, plural, count)

    flask_babel = _get_flask_babel_translation()
    if flask_babel is not None and hasattr(flask_babel, "npgettext"):
        return flask_babel.npgettext(context, singular, plural, count)

    translations = _get_builtin_translations()
    if hasattr(translations, "npgettext"):
        return translations.npgettext(context, singular, plural, count)

    return translations.ngettext(singular, plural, count)


pggetext = pgettext
