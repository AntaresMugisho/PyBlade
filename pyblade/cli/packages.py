"""Installing things with whatever the project already installs things with.

PyBlade does not own the environment it is run in. Somebody has chosen how this
project keeps its dependencies -- uv, Poetry, pipenv, a plain virtualenv -- and
a scaffolding tool that ignores that choice will at best put a package where
nobody is looking for it, and at worst fail outright: on Debian and its kin a
bare `pip install` into the system Python is refused, and rightly.

So the choice is read off the project rather than assumed: a lock file says it
first, what is on PATH says it second, and what the project wrote in its
pyblade.toml beats both. When nothing says anything and no virtualenv is
active, PyBlade installs nothing and prints the command to run instead.
"""

import shutil
import subprocess
import sys
from pathlib import Path

#: Each Python package manager, what shows it is the one in use, and how it is
#: asked to add a package. Order is the order they are looked for in.
PYTHON_MANAGERS = {
    "uv": {
        "marks": ("uv.lock",),
        "table": "tool.uv",
        "add": ("uv", "add"),
        "upgrade": ("uv", "add", "--upgrade"),
        # --no-workspace so that a project started inside another one is its own
        "create": ("uv", "init", "--bare", "--no-workspace"),
        "run": ("uv", "run"),
    },
    "poetry": {
        "marks": ("poetry.lock",),
        "table": "tool.poetry",
        "add": ("poetry", "add"),
        "upgrade": ("poetry", "update"),
        "create": ("poetry", "init", "-n"),
        "run": ("poetry", "run"),
    },
    "pipenv": {
        # Installing is what makes the Pipfile, so there is nothing to create
        "marks": ("Pipfile.lock", "Pipfile"),
        "table": None,
        "add": ("pipenv", "install"),
        "upgrade": ("pipenv", "update"),
        "create": None,
        "run": ("pipenv", "run"),
    },
}

#: The same for the JavaScript side.
JS_MANAGERS = {
    "pnpm": {"marks": ("pnpm-lock.yaml",), "add": ("pnpm", "add"), "run": ("pnpm", "exec")},
    "yarn": {"marks": ("yarn.lock",), "add": ("yarn", "add"), "run": ("yarn", "exec")},
    "bun": {"marks": ("bun.lockb", "bun.lock"), "add": ("bun", "add"), "run": ("bunx",)},
    "npm": {"marks": ("package-lock.json",), "add": ("npm", "install"), "run": ("npx",)},
}


#: Which manager a brand new project is given when nothing says otherwise.
#: uv first: it makes the project's environment and its dependency file in one
#: step, and needs nothing activated. A plain virtualenv is last because it is
#: the one that always works -- every machine running PyBlade can make one.
PREFERRED = ("uv", "poetry", "pipenv", "pip")

#: Where a project keeps its virtualenv when PyBlade makes one for it.
VENV_DIR = ".venv"


def in_virtualenv() -> bool:
    """Whether a virtualenv is active, which is the only place pip may write."""
    return sys.prefix != sys.base_prefix


def _has_table(root: Path, table: str) -> bool:
    """Whether the project's pyproject.toml holds the given dotted table."""
    import tomllib

    path = Path(root) / "pyproject.toml"
    if not path.exists():
        return False

    try:
        with open(path, "rb") as file:
            data = tomllib.load(file)
    except Exception:
        return False

    for part in table.split("."):
        if not isinstance(data, dict) or part not in data:
            return False
        data = data[part]

    return True


def _shown_by(root: Path, managers: dict) -> str:
    """Which manager the project itself shows it uses, or nothing.

    A lock file is the strongest thing anyone can say about how they install,
    so only what the project carries counts here. What happens to be installed
    on the machine says nothing about what this project wants.
    """
    root = Path(root)

    for name, manager in managers.items():
        if not shutil.which(name):
            continue

        if any((root / mark).exists() for mark in manager["marks"]):
            return name

        if manager.get("table") and _has_table(root, manager["table"]):
            return name

    return ""


def _first_installed(names) -> str:
    """The first of these that is on PATH."""
    return next((name for name in names if shutil.which(name)), "")


def detect_python_manager(root: Path | str = ".") -> str:
    """The Python package manager this project uses, or 'pip', or nothing.

    A project that shows nothing falls back to pip, but only inside an active
    virtualenv: writing to the system Python is not something PyBlade will do
    on anybody's behalf. Whatever is merely installed on the machine comes last,
    because using it would change a project that never asked for it.
    """
    return _shown_by(root, PYTHON_MANAGERS) or ("pip" if in_virtualenv() else "") or _first_installed(PYTHON_MANAGERS)


def detect_js_manager(root: Path | str = ".") -> str:
    """The JavaScript package manager this project uses, or nothing.

    npm before the others when the project shows no preference, because it is
    the one that comes with Node rather than the one somebody happens to have.
    """
    return _shown_by(root, JS_MANAGERS) or _first_installed(["npm", *JS_MANAGERS])


def python_install_command(manager: str, packages: list[str]) -> list[str] | None:
    """How to ask `manager` for these Python packages, or None if it cannot be asked."""
    if manager in PYTHON_MANAGERS:
        return [*PYTHON_MANAGERS[manager]["add"], *packages]

    if manager == "pip":
        # The interpreter that is running, never whichever `pip` is on PATH
        return [sys.executable, "-m", "pip", "install", *packages]

    return None


def js_install_command(manager: str, packages: list[str]) -> list[str] | None:
    """How to ask `manager` for these JavaScript packages, or None if it cannot be asked."""
    if manager in JS_MANAGERS:
        return [*JS_MANAGERS[manager]["add"], *packages]

    return None


def python_manager(root: Path | str = ".") -> str:
    """What this project installs Python packages with, its own word first."""
    from pyblade.config import config

    return config.stack.package_manager or detect_python_manager(root)


def js_manager(root: Path | str = ".") -> str:
    """What this project installs JavaScript packages with, its own word first."""
    from pyblade.config import config

    return config.stack.js_package_manager or detect_js_manager(root)


def python_upgrade_command(manager: str, packages: list[str]) -> list[str] | None:
    """How to ask `manager` to bring these Python packages up to date."""
    if manager in PYTHON_MANAGERS:
        return [*PYTHON_MANAGERS[manager]["upgrade"], *packages]

    if manager == "pip":
        return [sys.executable, "-m", "pip", "install", "--upgrade", *packages]

    return None


def js_run_command(manager: str, arguments: list[str]) -> list[str] | None:
    """How to ask `manager` to run a tool the project has installed.

    Every one of them ships a way to run a binary out of node_modules without
    it being on PATH, which is how a project's own Tailwind is run rather than
    whichever one happens to be installed on the machine.
    """
    if manager in JS_MANAGERS:
        return [*JS_MANAGERS[manager]["run"], *arguments]

    return None


# A PROJECT'S OWN ENVIRONMENT
# --------------------------------------------------------------------------------------------------------------------


def for_a_new_project() -> str:
    """The manager to give a project that has not got one, or nothing.

    Nothing is only possible on a machine with no Python to make a virtualenv
    with, which is not a machine PyBlade is running on.
    """
    return _first_installed(PREFERRED) or ("pip" if shutil.which(sys.executable) or sys.executable else "")


def venv_python(root: Path | str) -> Path | None:
    """The interpreter of the virtualenv PyBlade made for a project."""
    root = Path(root)

    for candidate in (root / VENV_DIR / "bin" / "python", root / VENV_DIR / "Scripts" / "python.exe"):
        if candidate.exists():
            return candidate

    return None


def create_environment_command(manager: str) -> list[str] | None:
    """How to give a new project a dependency file and an environment of its own.

    None when the manager needs none: pipenv makes both the moment something is
    installed, so there is nothing to do first.
    """
    if manager in PYTHON_MANAGERS:
        create = PYTHON_MANAGERS[manager].get("create")

        return list(create) if create else None

    if manager == "pip":
        return [sys.executable, "-m", "venv", VENV_DIR]

    return None


def environment_exists(manager: str, root: Path | str) -> bool:
    """Whether the project already has what create_environment_command would make.

    uv and Poetry both refuse to initialise a directory that already holds a
    pyproject.toml, which a project started in a directory somebody has already
    been working in may well do.
    """
    root = Path(root)

    if manager in ("uv", "poetry"):
        return (root / "pyproject.toml").exists()

    if manager == "pipenv":
        return (root / "Pipfile").exists()

    if manager == "pip":
        return venv_python(root) is not None

    return False


def project_install_command(manager: str, packages: list[str], root: Path | str) -> list[str] | None:
    """How to install into a project's own environment rather than the active one."""
    if manager in PYTHON_MANAGERS:
        return [*PYTHON_MANAGERS[manager]["add"], *packages]

    if manager == "pip":
        python = venv_python(root)

        return [str(python), "-m", "pip", "install", *packages] if python else None

    return None


def project_run_command(manager: str, arguments: list[str], root: Path | str) -> list[str] | None:
    """How to run something inside a project's own environment."""
    if manager in PYTHON_MANAGERS:
        return [*PYTHON_MANAGERS[manager]["run"], *arguments]

    if manager == "pip":
        python = venv_python(root)

        return [str(python), *arguments] if python else None

    return None


def django_admin_command(manager: str, root: Path | str) -> list[str] | None:
    """How to run django-admin out of a project's own environment.

    A virtualenv puts django-admin on a path of its own, so it is reached
    through the interpreter instead, which is the same program either way.
    """
    if manager == "pip":
        python = venv_python(root)

        return [str(python), "-m", "django"] if python else None

    return project_run_command(manager, ["django-admin"], root)


def activation_line(manager: str, name: str = ".") -> str:
    """What to tell somebody to type next, for the environment that was made."""
    enter = "" if name == "." else f"cd {name} && "

    if manager == "poetry":
        return f"{enter}poetry shell"

    if manager == "pipenv":
        return f"{enter}pipenv shell"

    return f"{enter}source {VENV_DIR}/bin/activate"


# RUNNING AN INSTALL
# --------------------------------------------------------------------------------------------------------------------


def install(command: list[str], cwd: Path | str | None = None) -> subprocess.CompletedProcess:
    """Run an install, giving back what it said rather than printing it."""
    return subprocess.run(command, cwd=str(cwd) if cwd else None, capture_output=True, text=True)


def as_typed(command: list[str]) -> str:
    """An install command written the way somebody would type it."""
    if command and command[0] == sys.executable:
        return " ".join(["python", *command[1:]])

    return " ".join(command)
