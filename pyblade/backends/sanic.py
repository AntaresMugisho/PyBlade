"""PyBlade in a Sanic application."""

from sanic.response import html

from . import base

configure = base.configure


def render(request, template_name: str, **context):
    """Render one of this application's templates as a response."""
    return html(base.render(base.shared_engine(), template_name, context, request))
