"""Where the components of a project are looked for.

A project keeps its components in one directory, `[paths] components` in its
pyblade.toml. A Django project may also keep some in the apps it is made of,
the way it keeps templates: an app's own `components` directory is looked for
after the project's, in the order the apps are installed. So the project can
always take over a component an app provides, and an app can bring its own.
"""

from pathlib import Path
from typing import NamedTuple

from pyblade.config import config


class ComponentRoot(NamedTuple):
    """A directory components live in, and how Python names the package it stands for."""

    directory: Path

    #: The dotted name of the directory as a Python package: the project's own
    #: is reached from the root of the project, which is where Python looks, an
    #: app's by the name of the app. None when it cannot be told.
    module: str | None = None


def django_apps() -> list:
    """The apps of a Django project, once it is ready to say which they are."""
    try:
        from django.apps import apps

        return list(apps.get_app_configs()) if apps.ready else []
    except Exception:
        return []


def _module_of(directory: Path) -> str | None:
    """The name Python knows a directory of the project by, told from the root of the project."""
    try:
        return ".".join(directory.resolve().relative_to(config.root.resolve()).parts) or None
    except ValueError:
        return None


def component_roots() -> list[ComponentRoot]:
    """The directories components are looked for in, the project's own first."""
    project = Path(config.paths.components)
    roots = [ComponentRoot(project, _module_of(project))]
    seen = {project.resolve()}

    for app in django_apps():
        directory = Path(app.path) / project.name
        resolved = directory.resolve()

        if resolved in seen or not directory.is_dir():
            continue

        seen.add(resolved)
        roots.append(ComponentRoot(directory, f"{app.name}.{project.name}"))

    return roots


def root_of(file) -> ComponentRoot | None:
    """The root a file lives in, if it lives in one."""
    resolved = Path(file).resolve()

    for root in component_roots():
        try:
            resolved.relative_to(root.directory.resolve())
        except ValueError:
            continue

        return root

    return None
