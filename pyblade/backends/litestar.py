"""PyBlade in a Litestar application."""

from litestar.response import Response

from . import base

configure = base.configure


def render(request, template_name: str, **context) -> Response:
    """Render one of this application's templates as a response."""
    return Response(
        content=base.render(base.shared_engine(), template_name, context, request),
        media_type="text/html",
    )
