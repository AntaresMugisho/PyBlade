"""PyBlade in a Sanic application.

    from pyblade.sanic import render

The binding itself is `pyblade.backends.sanic`; this is the name to import it by.
"""

from pyblade.backends.sanic import configure, render

__all__ = ["configure", "render"]
