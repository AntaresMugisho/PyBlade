"""PyBlade in a Flask application.

    from pyblade.flask import render

The binding itself is `pyblade.backends.flask`; this is the name to import it by.
"""

from pyblade.backends.flask import configure, engine, render, render_template

__all__ = ["configure", "engine", "render", "render_template"]
