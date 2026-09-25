"""PyBlade in a Quart application."""

from quart import Response, current_app

from . import base

configure = base.configure


def engine():
    """This application's engine, made from the template folder it declares."""
    app = current_app._get_current_object()

    return base.engine_for(app, app.template_folder)


async def render(template_name: str, **context) -> Response:
    """Render one of this application's templates as a response.

    A coroutine because Quart's own render_template is one, so that this can be
    awaited in the same place without anybody having to remember which is which.
    """
    return Response(base.render(engine(), template_name, context), content_type="text/html")


#: What a Quart application already calls it.
render_template = render
