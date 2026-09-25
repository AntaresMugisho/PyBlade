"""What every framework binding needs, so each one is only its own part.

Binding PyBlade to a web framework comes down to the same three things every
time: get hold of an engine, render a template by name with the request in its
context, and hand back whatever that framework calls an HTML response. Only the
last of those differs between frameworks, so only the last belongs in a
framework's own module.

Nothing here imports a web framework, and neither does importing PyBlade. A
framework module is imported by whoever uses that framework, and that is the
only point at which it has to be installed.
"""

from weakref import WeakKeyDictionary

from pyblade.config import config
from pyblade.engine.renderer import PyBlade

#: The engine an application gets when it has not asked for one of its own.
_shared: PyBlade | None = None

#: An engine per application object, for the frameworks that have one.
_per_app: "WeakKeyDictionary[object, PyBlade]" = WeakKeyDictionary()


def directories(*named) -> list[str]:
    """Where templates are looked for: what the caller said, or what the project says.

    A framework usually knows where its own templates are and says so. One that
    does not falls back to the project's own answer, which is `[paths]
    templates` in its pyblade.toml, so that the same setting works whichever
    framework is serving.
    """
    given = [str(directory) for directory in named if directory]

    return given or [str(config.paths.templates)]


def configure(*named) -> PyBlade:
    """Say where this application's templates are, and build its engine."""
    global _shared

    _shared = PyBlade(dirs=directories(*named))

    return _shared


def shared_engine() -> PyBlade:
    """The engine for an application that never said where its templates are."""
    return _shared if _shared is not None else configure()


def engine_for(app, *named) -> PyBlade:
    """The engine belonging to one application object.

    Flask and Quart can run several applications in one process, each with
    templates of its own, so an engine is kept per application -- weakly, so
    that an application going away takes its engine with it rather than leaving
    it behind in a dictionary nobody empties.
    """
    try:
        made = _per_app.get(app)
    except TypeError:
        # An application that cannot be weakly referenced shares the one engine
        return shared_engine()

    if made is None:
        made = PyBlade(dirs=directories(*named))
        _per_app[app] = made

    return made


def render(engine: PyBlade, template_name: str, context: dict, request=None) -> str:
    """A template of this project, rendered, as a string of HTML.

    `render_file` rather than `render`: the first takes the name of a template
    and loads it, the second takes the template itself. Handed a name, `render`
    would render the name.
    """
    if request is not None:
        context = {**context, "request": request}

    return engine.render_file(template_name, context)


def reset() -> None:
    """Forget every engine, for tests that build applications and drop them."""
    global _shared

    _shared = None
    _per_app.clear()
