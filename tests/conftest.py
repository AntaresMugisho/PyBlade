"""Test configuration.

Django is a development dependency and several parts of the engine talk to it,
so it is configured once here, for the whole suite, rather than being replaced
by mocks in each test module. Replacing a module the interpreter has really
imported leaks into every other test of the session.
"""

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="pyblade-test-secret-key",
        USE_I18N=False,
        USE_TZ=False,
        INSTALLED_APPS=["django.forms"],
        STATIC_URL="/static/",
        # What PyBlade itself serves -- the update endpoint, uploads and the
        # view that shows a file on its way -- so that a name may be reversed
        ROOT_URLCONF="pyblade.live.urls",
        MEDIA_URL="/media/",
        DATABASES={},
    )
    django.setup()


import pytest


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Every test starts with nothing counted against it.

    The throttle keeps its counts in Django's cache, which lives as long as the
    test run does. Without this, a module that makes enough requests from the
    same address would be refused by the counts of the tests before it.
    """
    from django.core.cache import cache

    cache.clear()
    yield
