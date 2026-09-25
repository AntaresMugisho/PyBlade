"""How PyBlade plugs into a web framework.

`PyBladeEngine` is Django's template backend: the class a Django project names
in its TEMPLATES setting. It is brought in when it is asked for rather than
when this package is, because importing PyBlade must not need Django.

The other frameworks have no such plugin point -- they are bound by a `render`
function, in a module of their own beside this one and reachable as
`pyblade.flask`, `pyblade.starlette` and so on.
"""

from importlib import import_module

__all__ = ["PyBladeEngine"]


def __getattr__(name):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(import_module("pyblade.backends.django"), name)

    # Kept, so the import happens once rather than on every attribute read
    globals()[name] = value

    return value


def __dir__():
    return sorted(__all__)
