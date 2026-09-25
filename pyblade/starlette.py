"""PyBlade in a Starlette application.

    from pyblade.starlette import render

The binding itself is `pyblade.backends.starlette`; this is the name to import it by.
"""

from pyblade.backends.starlette import configure, render

__all__ = ["configure", "render"]
