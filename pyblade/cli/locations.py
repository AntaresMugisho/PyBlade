"""Where the commands that write files put them.

They put them where the project says its templates and components are, read
from the root of the project rather than from wherever the command was run. In
a Django project they can also put them in one of its apps, which is where an
app that brings its own templates and components keeps them.
"""

import os
import sys
from pathlib import Path

from pyblade.config import config

#: What each kind of file is called in the `[paths]` table of pyblade.toml
KINDS = {"templates": "templates", "components": "components"}


class LocationError(Exception):
    """A place that was asked for and cannot be given."""


def setup_django() -> None:
    """Get a Django project ready to say which apps it is made of."""
    import django
    from django.apps import apps

    if apps.ready:
        return

    root = config.root
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        settings = Path(config.paths.settings or "")
        if not settings.name:
            raise LocationError("PyBlade doesn't know where the settings of this project are. Set [paths] settings.")

        os.environ["DJANGO_SETTINGS_MODULE"] = ".".join(settings.with_suffix("").parts)

    django.setup()


def app_directory(label: str) -> Path:
    """The directory of the Django app with this label."""
    if config.stack.framework != "django":
        raise LocationError("--app is for Django projects: this project doesn't use Django.")

    try:
        setup_django()
        from django.apps import apps

        return Path(apps.get_app_config(label).path)
    except LookupError:
        labels = ", ".join(sorted(app.label for app in apps.get_app_configs()))
        raise LocationError(f"There is no app labelled '{label}' in this project. Its apps are: {labels}.")
    except LocationError:
        raise
    except Exception as error:
        raise LocationError(f"PyBlade couldn't load the Django project to find the app '{label}': {error}")


def target_directory(kind: str, app: str | None = None) -> Path:
    """The directory to write templates or components in.

    The one the project says, from the root of the project, or the one an app
    of a Django project holds, under the same name.
    """
    declared = Path(getattr(config.paths, KINDS[kind]))

    if app:
        return app_directory(app) / declared.name

    return config.root / declared


def shown(path: Path) -> str:
    """A path as it is best told to somebody working where they ran the command."""
    try:
        return str(Path(path).relative_to(Path.cwd()))
    except ValueError:
        return str(path)
