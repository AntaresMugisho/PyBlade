"""What a project says about the way it is put together.

A PyBlade project describes itself in `pyblade.toml`, or in the `[tool.pyblade]`
table of its `pyproject.toml` for a project that would rather keep one file.
Every key has a default, so the file only holds what a project wants different.

A framework may have its own say: a Django project can write a `PYBLADE`
dictionary in its settings and what it holds wins over the file. Django is
asked that only once it is ready to answer, and asked again every time until it
is, so that importing PyBlade before `django.setup()` -- which the CLI, a
management command and the test suite all do -- cannot fail on it.
"""

import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - only reached on Pythons older than tomllib
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None


#: The files a project may describe itself in, in the order they are looked for.
CONFIG_FILES = ("pyblade.toml", "pyproject.toml")

#: What a project gets without saying anything.
DEFAULTS = {
    "project": {
        "name": "",
        "pyblade_version": "",
    },
    "stack": {
        "framework": "",
        "css_framework": "",
        "css_framework_version": "",
        "package_manager": "",
        "js_package_manager": "",
    },
    "paths": {
        "core": "",
        "settings": "",
        "templates": "templates",
        "components": "components",
        "commands": "management/commands",
    },
    "live": {
        "classes_dir": "live",
        "templates_dir": "live",
        "paginator": "",
        "throttle": {
            "enabled": True,
            "actions": "120/minute",
            "uploads": "20/minute",
            "max_body": "1mb",
            "max_streams": 16,
            "trust_forwarded": False,
        },
    },
    "i18n": {
        "locale": "en",
        "fallback_locale": "en",
        "directory": "locale",
        "domain": "pyblade",
        "languages": [],
    },
}

#: Keys whose value names a place on disk, and so is handed over as a Path.
PATH_KEYS = frozenset(
    {
        "paths.core",
        "paths.settings",
        "paths.templates",
        "paths.components",
        "paths.commands",
        "paths.root",
        "paths.stubs",
        "i18n.directory",
        "live.classes_dir",
        "live.templates_dir",
    }
)

#: Keys PyBlade works out for itself, which no file holds.
COMPUTED = ("paths.root", "paths.stubs")

#: Where a key read the old way now lives, so that code is told where it went.
MOVED = {
    "name": "project.name",
    "pyblade_version": "project.pyblade_version",
    "framework": "stack.framework",
    "css_framework": "stack.css_framework",
    "core_dir": "paths.core",
    "settings_path": "paths.settings",
    "root_dir": "paths.root",
    "stubs_dir": "paths.stubs",
    "templates_dir": "paths.templates",
    "components_dir": "paths.components",
    "commands_dir": "paths.commands",
    "default_locale": "i18n.locale",
    "locale_dir": "i18n.directory",
    "translation_domain": "i18n.domain",
    "languages": "i18n.languages",
}

#: What each table is for, written above it in the file PyBlade saves.
COMMENTS = {
    "project": "What this project is called.",
    "stack": "What it is built with.",
    "paths": "Where its parts are, relative to this file.",
    "live": "Live components.",
    "live.throttle": "How much a single client may ask for. See the docs before relaxing these.",
    "i18n": "Languages and translations.",
}

_MISSING = object()


def _lower(value):
    """The same mapping with every key lowercased, so a table may be written either way."""
    if not isinstance(value, dict):
        return value

    return {str(key).lower(): _lower(item) for key, item in value.items()}


def _merge(base: dict, over: dict) -> dict:
    """`base` with everything `over` says written on top of it, tables and all."""
    merged = dict(base)

    for key, value in over.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value

    return merged


def _dig(data, dotted, default=_MISSING):
    """Follow a dotted key into nested tables."""
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return default
        data = data[part]

    return data


def _plant(data: dict, dotted: str, value) -> None:
    """Put a value at a dotted key, making the tables above it as needed."""
    *tables, key = dotted.split(".")

    for part in tables:
        if not isinstance(data.get(part), dict):
            data[part] = {}
        data = data[part]

    data[key] = value


def _read_toml(path: Path) -> dict:
    """The TOML file at `path`, read."""
    if tomllib is None:  # pragma: no cover - only on Pythons older than tomllib
        raise RuntimeError(
            f"Reading {path.name} needs a TOML parser, which Python "
            f"{sys.version_info.major}.{sys.version_info.minor} has not got. "
            "Install 'tomli', or move to Python 3.11 or later."
        )

    with open(path, "rb") as file:
        return tomllib.load(file)


def _has_pyblade_table(path: Path) -> bool:
    """Whether a pyproject.toml is the one describing a PyBlade project."""
    try:
        return bool(_read_toml(path).get("tool", {}).get("pyblade"))
    except Exception:
        return False


def find_config_file(start: Path | None = None) -> Path | None:
    """The file describing the project `start` is inside, if there is one.

    Looked for from `start` upwards, so that a command run deep inside a project
    finds it. A pyproject.toml counts only when it holds a [tool.pyblade] table,
    or every Python project would look like a PyBlade one.
    """
    current = Path(start) if start else Path.cwd()

    for directory in [current, *current.parents]:
        for name in CONFIG_FILES:
            candidate = directory / name
            if not candidate.exists():
                continue

            if name == "pyproject.toml" and not _has_pyblade_table(candidate):
                continue

            return candidate

    return None


class Section:
    """One table of the configuration, reached by name: `config.i18n.locale`."""

    def __init__(self, config, path):
        object.__setattr__(self, "_config", config)
        object.__setattr__(self, "_path", path)

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)

        return self._config.read(f"{self._path}.{key}")

    def __setattr__(self, key, value):
        self._config.write(f"{self._path}.{key}", value)

    def get(self, dotted: str, default=None):
        """What this table says at a dotted key, or `default` if it says nothing."""
        try:
            return self._config.read(f"{self._path}.{dotted}")
        except AttributeError:
            return default

    def as_dict(self) -> dict:
        """Everything this table holds, defaults and all."""
        return self._config.as_dict(self._path)

    def __repr__(self):
        return f"<{self._path} {self.as_dict()}>"


class Config:
    """Everything a project says about itself, however it says it."""

    def __init__(self, config_file: str | Path | None = None):
        self._explicit = Path(config_file) if config_file else None
        self._file_path = self._explicit or find_config_file()

        # What the file says, which is what save() writes back
        self._file = {}

        # What the framework's settings say, once they can be asked, beside the
        # very dictionary they were read from so a change to it is noticed
        self._framework = {}
        self._framework_raw = None

        # What this run has said, which wins over both and is never written
        self._runtime = {}

        self.load()

    # READING
    # ------------------------------------------------------------------------------------------------------------

    @property
    def path(self) -> Path | None:
        """The file this configuration was read from, if there was one."""
        return self._file_path

    @property
    def root(self) -> Path:
        """The directory the project lives in."""
        runtime = _dig(self._runtime, "paths.root", None)
        if runtime:
            return Path(runtime)

        return self._file_path.parent if self._file_path else Path.cwd()

    def read(self, dotted: str):
        """What the configuration says at a dotted key.

        The last word goes to this run, then to the framework's own settings,
        then to the file, and failing all of those to the default.
        """
        if dotted == "paths.root":
            return self.root

        if dotted == "paths.stubs":
            return Path(__file__).parent / "cli" / "stubs"

        default = _dig(DEFAULTS, dotted)

        for source in (self._runtime, self._overlay(), self._file):
            value = _dig(source, dotted)
            if value is not _MISSING:
                break
        else:  # pragma: no cover - the loop always binds `value`
            value = _MISSING

        if value is _MISSING:
            value = default

        if value is _MISSING:
            raise AttributeError(self._unknown(dotted))

        if isinstance(value, dict):
            return Section(self, dotted)

        if dotted in PATH_KEYS:
            return Path(value) if value else None

        return value

    def write(self, dotted: str, value) -> None:
        """Say something, to be written out by the next save()."""
        if dotted in COMPUTED:
            _plant(self._runtime, dotted, str(value) if value else "")
            return

        _plant(self._file, dotted, str(value) if isinstance(value, Path) else value)

    def as_dict(self, path: str | None = None) -> dict:
        """Everything the configuration says, defaults and all."""
        merged = _merge(_merge(deepcopy(DEFAULTS), self._file), self._overlay())
        merged = _merge(merged, self._runtime)

        return merged if path is None else _dig(merged, path, {})

    def _unknown(self, dotted: str) -> str:
        """What to say about a key PyBlade has never had."""
        name = dotted.split(".")[-1]

        if dotted in MOVED:
            return f"'{dotted}' moved to '{MOVED[dotted]}' when the configuration moved into tables."

        if name in MOVED:
            return f"'{name}' moved to '{MOVED[name]}' when the configuration moved into tables."

        return f"PyBlade has no '{dotted}' setting."

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)

        return self.read(key)

    def get(self, dotted: str, default=None):
        """What the configuration says at a dotted key, or `default` if it says nothing."""
        try:
            return self.read(dotted)
        except AttributeError:
            return default

    @property
    def DEBUG(self) -> bool:
        """Whether the project is being run by whoever is writing it.

        Asked of the framework that is serving, which is the one that knows.
        The project may say which that is; a project that never said is asked
        of each in turn, so that a template which goes wrong is explained
        rather than silently swallowed for want of a line in pyblade.toml.
        """
        named = self.stack.framework

        for framework in ("django", "flask", "fastapi"):
            if named and named != framework:
                continue

            debug = self._framework_debug(framework)
            if debug is not None:
                return debug

        return False

    @staticmethod
    def _framework_debug(framework: str):
        """What a framework says about being in development, or None if it is not the one serving."""
        if framework == "django":
            try:
                from django.conf import settings as django_settings

                # A project that has not configured Django is not being served
                # by it, whatever it may have imported
                return bool(django_settings.DEBUG) if django_settings.configured else None
            except Exception:
                return None

        if framework == "flask":
            try:
                from flask import current_app

                return bool(current_app.debug)
            except Exception:
                return None

        if framework == "fastapi":
            # FastAPI has no debug setting of its own, so the environment says
            import os

            flag = os.getenv("DEBUG")

            return flag.lower() == "true" if flag is not None else None

        return None

    # THE FRAMEWORK'S OWN SETTINGS
    # ------------------------------------------------------------------------------------------------------------

    def _overlay(self) -> dict:
        """What the framework that is serving says, once it is able to say it.

        A framework is only asked when it is ready. Until then this is empty and
        nothing is remembered, so that the first read after the framework has
        started up picks its settings up. That is what makes importing PyBlade
        at any point safe, whatever the framework has or has not done yet.
        """
        try:
            from django.conf import settings as django_settings

            if not django_settings.configured:
                return {}

            said = getattr(django_settings, "PYBLADE", None) or {}
        except Exception:
            return {}

        # Read afresh whenever the settings hand over a different dictionary, so
        # that a project overriding its settings in a test is followed
        if said is not self._framework_raw:
            self._framework_raw = said
            self._framework = _lower(said)

        return self._framework

    def reload(self) -> None:
        """Read everything again, forgetting what the framework had said."""
        self._framework = {}
        self._framework_raw = None
        self._file_path = self._explicit or find_config_file()
        self.load()

    @contextmanager
    def override(self, values: dict | None = None, **named):
        """Say something different for as long as the block runs.

        Written for tests, which need a project's layout to be somewhere other
        than where it is. Keys are dotted: `config.override({"paths.templates": tmp})`.
        """
        values = {**(values or {}), **named}
        saved = deepcopy(self._runtime)

        try:
            for dotted, value in values.items():
                _plant(self._runtime, dotted, str(value) if isinstance(value, Path) else value)
            yield self
        finally:
            self._runtime = saved

    # WRITING
    # ------------------------------------------------------------------------------------------------------------

    def load(self) -> None:
        """Read the file describing the project, if it has one."""
        path = self._file_path

        if path is None or not path.exists():
            self._file = {}
            return

        data = _read_toml(path)
        if path.name == "pyproject.toml":
            data = data.get("tool", {}).get("pyblade", {})

        self._file = _lower(data)

    def save(self, path: str | Path | None = None) -> Path:
        """Write out what the project says that a default does not already say.

        The file is written from the schema, in its order and with its comments,
        so it reads the same whoever saved it last. Only what differs from the
        default is kept, so that a project follows PyBlade when PyBlade changes
        its mind -- and so a comment written into the file by hand does not
        survive a save.
        """
        target = Path(path) if path else self._file_path

        if target is None:
            target = Path.cwd() / "pyblade.toml"

        if target.name == "pyproject.toml":
            raise RuntimeError(
                "PyBlade will not rewrite your pyproject.toml. "
                "Move its [tool.pyblade] table into a pyblade.toml to have PyBlade keep it up to date."
            )

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dumps(_differences(self._file)))

        self._file_path = target
        self._explicit = self._explicit and target

        return target


def _differences(data: dict, defaults: dict = DEFAULTS) -> dict:
    """What `data` says that `defaults` does not already say."""
    different = {}

    for key, value in data.items():
        default = defaults.get(key, _MISSING) if isinstance(defaults, dict) else _MISSING

        if isinstance(value, dict):
            nested = _differences(value, default if isinstance(default, dict) else {})
            if nested:
                different[key] = nested
        elif value != default:
            different[key] = value

    return different


def dumps(data: dict) -> str:
    """A configuration written out as TOML, in the order the schema declares it."""
    lines = ["# How this project is put together. See https://docs.pyblade.com/docs/configuration.", ""]
    _dump_table(data, [], lines)

    return "\n".join(lines).rstrip() + "\n"


def _dump_table(data: dict, path: list[str], lines: list[str]) -> None:
    """Write one table and then the tables inside it, scalars first."""
    ordered = _dig(DEFAULTS, ".".join(path)) if path else DEFAULTS
    order = list(ordered) if isinstance(ordered, dict) else []
    keys = [key for key in order if key in data] + [key for key in data if key not in order]

    scalars = [key for key in keys if not isinstance(data[key], dict)]
    tables = [key for key in keys if isinstance(data[key], dict)]

    if scalars and path:
        header = ".".join(path)
        if header in COMMENTS:
            lines.append(f"# {COMMENTS[header]}")
        lines.append(f"[{header}]")

    for key in scalars:
        lines.append(f"{key} = {_dump_value(data[key])}")

    if scalars:
        lines.append("")

    for key in tables:
        _dump_table(data[key], [*path, key], lines)


def _dump_value(value) -> str:
    """One value, written the way TOML writes it."""
    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, int) or isinstance(value, float):
        return repr(value)

    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_dump_value(item) for item in value) + "]"

    text = str(value).replace("\\", "\\\\").replace('"', '\\"')

    return f'"{text}"'


config = Config()

#: The name this was known by before the tables; the very same configuration.
settings = config
