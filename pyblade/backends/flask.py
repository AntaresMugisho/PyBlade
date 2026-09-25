"""PyBlade in a Flask application."""

from flask import Response, current_app

from . import base

configure = base.configure


def engine():
    """This application's engine, made from the template folder it declares."""
    app = current_app._get_current_object()

    return base.engine_for(app, app.template_folder)


def render(template_name: str, **context) -> Response:
    """Render one of this application's templates as a response."""
    return Response(base.render(engine(), template_name, context), mimetype="text/html")


#: What a Flask application already calls it.
render_template = render
