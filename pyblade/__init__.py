"""PyBlade: a template engine, and live components built on it.

Everything that needs a web framework installed is imported when it is asked
for rather than when PyBlade is. `pyblade init` exists to start a project with
a framework that is not installed yet -- so importing PyBlade, which the CLI
does before it can do anything at all, must not need one.
"""

from importlib import import_module

from .cli.base import BaseCommand
from .config import config
from .engine import contexts, exceptions, loader, template
from .engine.renderer import PyBlade

#: What lives behind a web framework, and the module each one comes from.
_FRAMEWORK_BOUND = {
    "LiveComponent": "pyblade.live.base",
    "ComponentMixin": "pyblade.live.mixins",
    "decorators": "pyblade.live.decorators",
}

__all__ = [
    "BaseCommand",
    "ComponentMixin",
    "LiveComponent",
    "PyBlade",
    "config",
    "contexts",
    "decorators",
    "exceptions",
    "loader",
    "settings",
    "template",
]


def __getattr__(name):
    """Bring in a framework-bound name the first time somebody asks for it."""
    if name not in _FRAMEWORK_BOUND:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(_FRAMEWORK_BOUND[name])
    value = module if name == "decorators" else getattr(module, name)

    # Kept, so the import happens once rather than on every attribute read
    globals()[name] = value

    return value


def __dir__():
    return sorted(__all__)
