"""PyBlade in a Litestar application.

    from pyblade.litestar import render

The binding itself is `pyblade.backends.litestar`; this is the name to import it by.
"""

from pyblade.backends.litestar import configure, render

__all__ = ["configure", "render"]
