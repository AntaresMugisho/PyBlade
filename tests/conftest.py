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
        USE_I18N=False,
        USE_TZ=False,
        INSTALLED_APPS=["django.forms"],
        STATIC_URL="/static/",
        MEDIA_URL="/media/",
        DATABASES={},
    )
    django.setup()
