"""PyBlade in a FastAPI application.

FastAPI's responses are Starlette's, so this is that binding under the name
somebody writing FastAPI will look for.
"""

from .starlette import configure, render

__all__ = ["configure", "render"]
