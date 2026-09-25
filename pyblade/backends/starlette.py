"""PyBlade in a Starlette application."""

from starlette.responses import HTMLResponse

from . import base

configure = base.configure


def render(request, template_name: str, **context) -> HTMLResponse:
    """Render one of this application's templates as a response."""
    return HTMLResponse(base.render(base.shared_engine(), template_name, context, request))
