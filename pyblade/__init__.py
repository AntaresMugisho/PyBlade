"""PyBlade: a template engine, and live components built on it.

Nothing here needs a web framework. `pyblade init` exists to start a project
with a framework that is not installed yet, and the CLI imports PyBlade before
it can do anything at all, so importing PyBlade must not need one.

A framework is bound by importing its own module, which is the point at which
it does have to be installed:

    from pyblade import PyBlade
    from pyblade.flask import render
    from pyblade.starlette import render

Django is the exception: it is bound by its template backend rather than by a
render function, and a project names `pyblade.backends.PyBladeEngine` in its
TEMPLATES setting.
"""

from importlib import import_module

from .cli.base import BaseCommand
from .config import config
from .engine import contexts, exceptions, loader, template
from .engine.renderer import PyBlade

#: Names that are a module of their own, imported the first time one is asked
#: for. Every one of them needs something PyBlade itself does not.
_LAZY_MODULES = {
    "decorators": "pyblade.live.decorators",
    "django": "pyblade.django",
    "fastapi": "pyblade.fastapi",
    "flask": "pyblade.flask",
    "litestar": "pyblade.litestar",
    "quart": "pyblade.quart",
    "sanic": "pyblade.sanic",
    "starlette": "pyblade.starlette",
}

#: Names that live inside a module, imported the same way and for the same reason.
_LAZY_NAMES = {
    "ComponentMixin": "pyblade.live.mixins",
    "LiveComponent": "pyblade.live.base",
}

__all__ = [
    "BaseCommand",
    "ComponentMixin",
    "LiveComponent",
    "PyBlade",
    "config",
    "contexts",
    "decorators",
    "django",
    "exceptions",
    "fastapi",
    "flask",
    "litestar",
    "loader",
    "quart",
    "sanic",
    "starlette",
    "template",
]


def __getattr__(name):
    """Bring in a name that needs a web framework, the first time it is asked for."""
    if name in _LAZY_MODULES:
        value = import_module(_LAZY_MODULES[name])
    elif name in _LAZY_NAMES:
        value = getattr(import_module(_LAZY_NAMES[name]), name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    # Kept, so the import happens once rather than on every attribute read
    globals()[name] = value

    return value


def __dir__():
    return sorted(__all__)
