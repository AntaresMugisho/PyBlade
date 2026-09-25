import keyword
import re
import subprocess
from pathlib import Path

from questionary import Choice

from pyblade.cli import BaseCommand, packages, tailwind
from pyblade.config import Config
from pyblade.utils import get_version

_SETTINGS_PATERN = re.compile(
    r"\"\"\"(?P<banner>.*?)\"\"\"\s*.*?\s*INSTALLED_APPS\s=\s\[\s*(?P<installed_apps>.*?)\s*\]\s*.*?\s*MIDDLEWARE\s=\s\[\s*(?P<middleware>.*?)\s*\]\s*.*?\s*TEMPLATES\s=\s*\[\s*(?P<templates>\{.*?\},)\n\]",
    re.DOTALL,
)

# Django's own engine is kept beside PyBlade's: the admin and anything else that
# ships Django templates goes on rendering, while everything in templates/ is
# rendered by PyBlade.
_TEMPLATES = """{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
    {
        "BACKEND": "pyblade.django.PyBladeEngine",
        "NAME": "pyblade",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },"""


class Command(BaseCommand):
    """
    Start a new PyBlade-powered project.
    """

    name = "init"

    #: What the new project is given to run on.
    REQUIRES = ["django", "pyblade"]

    #: The name that means "here" rather than a directory to make.
    HERE = "."

    #: What says a directory already holds a project, so starting one in it
    #: would write over somebody's work.
    ALREADY_A_PROJECT = ("manage.py", "pyblade.toml", "pyproject.toml")

    def config(self):
        self.add_option(
            "--package-manager",
            help=f"What the new project manages its dependencies with ({', '.join(packages.PREFERRED)})",
        )

    def handle(self, **kwargs):
        try:
            self.project = self.form(
                name=self.ask("What is your project name ? (. for the current directory)", default="my_project"),
                framework=self.choice(
                    "Which Python web framework would you like to use?",
                    choices=[Choice("Django", "django"), Choice("Flask", "flask"), Choice("FastAPI", "fastapi")],
                ),
                tailwind=self.confirm("Would you like to configure Tailwind CSS?", True),
            )
        except KeyboardInterrupt:
            self.info("Aborted by user !")
            return

        self.directory = Path.cwd() if self.project.name == self.HERE else Path(self.project.name)

        if not self._place_is_free():
            return

        self.package = self._package_name()
        if self.package is None:
            return

        self.line(f"""
    Project details :
        - Project name : [bold]{self.package}[/bold]
        - Where : [bold]{self.directory}[/bold]
        - Framework : [bold]{self.project.framework.capitalize()}[/bold]
        - Tailwind CSS : [bold]{"yes" if self.project.tailwind else "no"}[/bold]
    """)

        if not self.confirm("Is this correct?", True):
            self.info("Aborted by user.")
            return

        self.manager = kwargs.get("package_manager") or packages.for_a_new_project()

        if not self._start_project():
            return

        self._configure_pyblade()

        if self.project.tailwind:
            self._configure_tailwind()

        self.success(
            f"Your [bold]{self.project.framework.capitalize()}[/bold] project powered by "
            "PyBlade was created and configured successfully."
        )
        self.line(f"""
    Next :
        [blue]{packages.activation_line(self.manager, self.project.name)}[/blue]
        [blue]pyblade dev[/blue]
    """)

    # WHERE THE PROJECT GOES, AND WHAT IT IS CALLED
    # ----------------------------------------------------------------------------------------------------------------

    def _place_is_free(self) -> bool:
        """Whether a project may be started here without writing over one."""
        if self.project.name == self.HERE:
            held = [name for name in self.ALREADY_A_PROJECT if (self.directory / name).exists()]

            if held:
                self.error(
                    f"This directory already holds a project ({', '.join(held)})."
                    " Start a new one somewhere else, or give it a name of its own."
                )
                return False

            return True

        if self.directory.exists():
            self.error(
                f"A project with the name '{self.project.name}' already exists."
                " Consider choosing a different name for your new project."
            )
            return False

        return True

    def _package_name(self) -> str | None:
        """What the project's Python package is called.

        The name given, except when it is '.': a directory is free to be called
        'my-shop' and a Python package is not, so the name is read off the
        directory and tidied. Anything that cannot be tidied into a name is not
        guessed at -- the project is asked for one.
        """
        if self.project.name != self.HERE:
            return self.project.name

        tidied = re.sub(r"[^0-9a-zA-Z_]+", "_", self.directory.resolve().name).strip("_")

        if not tidied.isidentifier() or keyword.iskeyword(tidied):
            self.error(
                f"'{self.directory.resolve().name}' does not make a usable Python package name"
                f"{f' ({tidied!r})' if tidied else ''}."
                " Run this again with a name instead of '.'."
            )
            return None

        return tidied

    # STARTING THE PROJECT
    # ----------------------------------------------------------------------------------------------------------------

    def _start_project(self) -> bool:
        """Lay the project out, with an environment and dependencies of its own.

        PyBlade does not install into whatever environment happens to be active
        when this is run. The new project gets its own -- its dependency file,
        its virtualenv, its Django -- so that what was just created can be run,
        and so that nothing anybody else owns is written to.
        """
        if self.project.framework != "django":
            self.error(f"PyBlade cannot start a {self.project.framework} project yet.")
            return False

        if not self.manager:
            self.error("PyBlade found no way to manage this project's dependencies. Install uv and run this again.")
            return False

        root = self.directory
        root.mkdir(parents=True, exist_ok=True)

        # A project started in a directory somebody has already worked in may
        # already have the dependency file the manager would otherwise make
        setup = None if packages.environment_exists(self.manager, root) else self.manager
        steps = [
            ("Setting the project up", packages.create_environment_command(setup) if setup else None),
            (
                f"Installing {' and '.join(self.REQUIRES)}",
                packages.project_install_command(self.manager, self.REQUIRES, root),
            ),
        ]

        for message, command in steps:
            if command is None:
                continue

            if not self._run(command, root, message):
                return False

        # `.` so that manage.py lands beside the dependency file rather than in
        # a directory of its own inside the project
        admin = packages.django_admin_command(self.manager, root)

        if admin is None:
            self.error(f"PyBlade could not find django-admin in the environment {self.manager} made.")
            return False

        return self._run([*admin, "startproject", self.package, "."], root, "Starting a new Django project")

    def _run(self, command: list[str], cwd: Path, message: str) -> bool:
        """Run one step of the setup, saying what failed if it does."""
        with self.status(f"{message} with [bold]{self.manager}[/bold]..."):
            result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)

        if result.returncode != 0:
            self.error(f"`{packages.as_typed(command)}` failed:\n{(result.stderr or result.stdout).strip()}")
            return False

        self.success(message + ".", bold=False)

        return True

    # CONFIGURING PYBLADE
    # ----------------------------------------------------------------------------------------------------------------

    def _configure_pyblade(self):
        """Configures PyBlade for the project."""

        self.settings = Config(config_file=self.directory / "pyblade.toml")

        self.settings.project.name = self.package
        self.settings.project.pyblade_version = get_version()
        self.settings.stack.framework = self.project.framework
        self.settings.paths.settings = f"{self.package}/settings.py"

        # Written down because it is now a fact rather than a guess: this is
        # what the project's dependencies were just installed with.
        self.settings.stack.package_manager = self.manager
        self.settings.save()

        # Said for this run only, so that no absolute path reaches a file that
        # might be published on a different machine
        self.settings.paths.root = Path(self.project.name)

        for directory in ("templates", "static/css", "static/js"):
            Path(self.settings.root, directory).mkdir(parents=True, exist_ok=True)

        if self.project.framework == "django":
            self._configure_django_settings()

        self.success("PyBlade Engine has been configured successfully.")

    def _configure_django_settings(self):
        """Put PyBlade's engine into the project's settings, beside Django's own."""
        settings_file = self.settings.root / self.settings.paths.settings

        try:
            settings = settings_file.read_text()

            match = re.search(_SETTINGS_PATERN, settings)
            if not match:
                self.warning(
                    f"PyBlade could not find the TEMPLATES setting in {self.settings.paths.settings}. "
                    "Add the PyBladeEngine backend to it yourself."
                )
                return

            settings_file.write_text(settings.replace(match.group("templates"), _TEMPLATES))
        except Exception as e:
            self.error(f"Failed to properly configure PyBlade: {e!s}")

    # CONFIGURING TAILWIND
    # ----------------------------------------------------------------------------------------------------------------

    def _configure_tailwind(self):
        """Install Tailwind and set the project up to build its stylesheet."""
        root = self.settings.root
        manager = packages.detect_js_manager(root)

        if manager:
            with self.status(f"Installing Tailwind CSS with {manager}..."):
                command = packages.js_install_command(manager, tailwind.PACKAGES)
                result = packages.install(command, cwd=root)

            if result.returncode != 0:
                self.warning(
                    f"`{packages.as_typed(command)}` failed, so Tailwind is configured but not installed:\n"
                    f"{result.stderr.strip()}"
                )
                manager = ""
            else:
                self.settings.stack.js_package_manager = manager
        else:
            self.warning(
                "No JavaScript package manager was found, so Tailwind is configured but not installed.\n"
                f" Install Node, then run: npm install {' '.join(tailwind.PACKAGES)}"
            )

        tailwind.configure(root, self.settings.paths.stubs, [self.settings.paths.templates, "components"])

        self.settings.stack.css_framework = "tailwindcss"
        self.settings.stack.css_framework_version = "4"
        self.settings.save()

        self.success("Tailwind CSS has been configured successfully.")
