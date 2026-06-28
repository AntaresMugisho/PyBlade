"""
PyBlade i18n helper module for framework integration.

This module provides translation functions that can be passed to template
context to enable internationalization in PyBlade templates.

It uses Python's standard gettext module and is designed to be framework-agnostic
while maintaining compatibility with Django, Flask, FastAPI, etc.
"""

import gettext
import os
from pathlib import Path
from typing import Callable, Dict, Optional


class I18nContext:
    """
    Manages gettext translation context for PyBlade templates.

    This class loads translation files (.mo) and provides translation functions
    that can be passed to template context as _gettext, _pgettext, _ngettext, _npgettext.
    """

    def __init__(
        self,
        locale_dir: str = "locale",
        domain: str = "pyblade",
        locale: Optional[str] = None,
    ):
        """
        Initialize the i18n context.

        Args:
            locale_dir: Path to the locale directory (default: "locale")
            domain: Gettext domain to use (default: "pyblade")
            locale: Locale code (e.g., "fr", "de", "es"). If None, uses system default.
        """
        self.locale_dir = Path(locale_dir)
        self.domain = domain
        self.locale = locale
        self._translations = None
        self._load_translations()

    def _load_translations(self):
        """Load gettext translations for the specified locale."""
        if not self.locale_dir.exists():
            return

        # Determine locale to use
        locale = self.locale or self._get_system_locale()

        # Try to load the translation
        try:
            self._translations = gettext.translation(
                self.domain,
                localedir=str(self.locale_dir),
                languages=[locale],
                fallback=True,
            )
        except Exception:
            # Fallback to NullTranslations if loading fails
            self._translations = gettext.NullTranslations()

    def _get_system_locale(self) -> str:
        """Get the system's default locale."""
        import locale

        try:
            return locale.getdefaultlocale()[0] or "en_US"
        except Exception:
            return "en_US"

    def get_context(self) -> Dict[str, Callable]:
        """
        Get translation functions for template context.

        Returns a dictionary with translation functions that should be passed
        to the template rendering context:

        ```python
        context = {
            "_gettext": gettext_func,
            "_pgettext": pgettext_func,
            "_ngettext": ngettext_func,
            "_npgettext": npgettext_func,
        }
        ```

        Returns:
            Dictionary with translation functions
        """
        if self._translations is None:
            self._load_translations()

        t = self._translations

        return {
            "_gettext": t.gettext,
            "_pgettext": lambda ctx, msg: t.gettext(msg),  # Simple fallback
            "_ngettext": t.ngettext,
            "_npgettext": lambda ctx, s, p, n: t.ngettext(s, p, n),  # Simple fallback
        }

    def set_locale(self, locale: str):
        """
        Change the current locale and reload translations.

        Args:
            locale: New locale code (e.g., "fr", "de", "es")
        """
        self.locale = locale
        self._load_translations()

    def gettext(self, message: str) -> str:
        """
        Translate a singular message.

        Args:
            message: The message to translate

        Returns:
            Translated message
        """
        if self._translations is None:
            self._load_translations()
        return self._translations.gettext(message)

    def ngettext(self, singular: str, plural: str, count: int) -> str:
        """
        Translate a message with pluralization.

        Args:
            singular: Singular form of the message
            plural: Plural form of the message
            count: The count to determine which form to use

        Returns:
            Translated message in appropriate form
        """
        if self._translations is None:
            self._load_translations()
        return self._translations.ngettext(singular, plural, count)


def get_i18n_context(
    locale_dir: str = "locale",
    domain: str = "pyblade",
    locale: Optional[str] = None,
) -> Dict[str, Callable]:
    """
    Convenience function to get translation functions for template context.

    This is a shortcut for creating an I18nContext and getting its context dict.

    Args:
        locale_dir: Path to the locale directory (default: "locale")
        domain: Gettext domain to use (default: "pyblade")
        locale: Locale code (e.g., "fr", "de", "es"). If None, uses system default.

    Returns:
        Dictionary with translation functions for template context

    Example:
        ```python
        from pyblade.engine.i18n import get_i18n_context

        # Get translation functions
        i18n_context = get_i18n_context(locale="fr", domain="pyblade")

        # Pass to template rendering
        template.render({**context, **i18n_context})
        ```
    """
    i18n = I18nContext(locale_dir=locale_dir, domain=domain, locale=locale)
    return i18n.get_context()


def configure_django_integration():
    """
    Configure PyBlade to use Django's translation system.

    This function sets up PyBlade to use Django's i18n functions when Django is available.
    Call this in your Django app's configuration or before rendering templates.

    Example:
        ```python
        from pyblade.engine.i18n import configure_django_integration

        configure_django_integration()
        ```
    """
    try:
        from django.utils.translation import gettext, ngettext, pgettext, npgettext

        # Create a wrapper that returns Django functions
        def django_i18n_context():
            return {
                "_gettext": gettext,
                "_pgettext": pgettext,
                "_ngettext": ngettext,
                "_npgettext": npgettext,
            }

        return django_i18n_context
    except ImportError:
        # Django not available, return None
        return None


def configure_flask_integration(app):
    """
    Configure PyBlade to use Flask-Babel's translation system.

    This function integrates PyBlade with Flask-Babel for Flask applications.

    Args:
        app: Flask application instance

    Example:
        ```python
        from flask import Flask
        from flask_babel import Babel
        from pyblade.engine.i18n import configure_flask_integration

        app = Flask(__name__)
        babel = Babel(app)

        configure_flask_integration(app)
        ```
    """
    try:
        from flask_babel import gettext, ngettext, pgettext, npgettext

        def flask_i18n_context():
            return {
                "_gettext": gettext,
                "_pgettext": pgettext,
                "_ngettext": ngettext,
                "_npgettext": npgettext,
            }

        # Store the context function in app config
        app.config["PYBLADE_I18N_CONTEXT"] = flask_i18n_context

        return flask_i18n_context
    except ImportError:
        # Flask-Babel not available
        return None


def configure_fastapi_integration():
    """
    Configure PyBlade to use FastAPI's translation system.

    This function provides a context function for FastAPI applications.
    For FastAPI, you typically need to set up your own gettext integration
    using a library like fastapi-babel.

    Example:
        ```python
        from pyblade.engine.i18n import configure_fastapi_integration

        i18n_context_func = configure_fastapi_integration()
        # Then use i18n_context_func() to get translation functions
        ```
    """
    # FastAPI doesn't have built-in i18n, so we provide a standard gettext setup
    def fastapi_i18n_context(locale_dir: str = "locale", domain: str = "pyblade", locale: Optional[str] = None):
        return get_i18n_context(locale_dir=locale_dir, domain=domain, locale=locale)

    return fastapi_i18n_context
