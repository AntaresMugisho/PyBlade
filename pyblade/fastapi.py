"""PyBlade in a Fastapi application.

    from pyblade.fastapi import render

The binding itself is `pyblade.backends.fastapi`; this is the name to import it by.
"""

from pyblade.backends.fastapi import configure, render

__all__ = ["configure", "render"]
