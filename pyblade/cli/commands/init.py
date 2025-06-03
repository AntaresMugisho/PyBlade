import re
from pathlib import Path

from questionary import Choice

from pyblade.cli import BaseCommand
from pyblade.cli.exceptions import RunError
from pyblade.cli.utils import run_command
from pyblade.config import settings
from pyblade.utils import get_version

_SETTINGS_PATERN = re.compile(
    r"\"\"\"(?P<banner>.*?)\"\"\"\s*.*?\s*INSTALLED_APPS\s=\s\[\s*(?P<installed_apps>.*?)\s*\]\s*.*?\s*MIDDLEWARE\s=\s\[\s*(?P<middleware>.*?)\s*\]\s*.*?\s*TEMPLATES\s=\s*\[\s*(?P<templates>\{.*?\},)\n\]",  # noqa E501
    re.DOTALL,
)


class Command(BaseCommand):
    """
    Start a new PyBlade-powered project.
    """

    name = "init"

    def handle(self, **kwargs):

        # Collect project info
        self.project = self.form(
            name=self.ask("What is your project name?", default="my_project"),
            framework=self.choice(
                "Which Python web framework would you like to use?", choices=[Choice("Django", "django")]
            ),
            css_framework=self.choice(
                "Would you like to configure a CSS framework?",
                choices=["Tailwind 4", "Bootstrap 5", Choice("Not sure", False)],
            ),
        )

        # Confirm project details
        self.line(
            f"""
Project details :
    - Project name : [bold]{self.project.name}[/bold]
    - Framework : [bold]{self.project.framework.capitalize()}[/bold]
    - CSS framework : [bold]{self.project.css_framework or 'None'}[/bold]
"""
        )

        if not self.confirm("Is this correct?"):
            self.info("Cancelled by user.")
            return

        # Generate project
        with self.status("Installing Python dependencies ...") as status:
            # Install python web framework
            self._pip_install(self.project.framework)

            # Install CSS Framework
            if self.project.css_framework:
                if "tailwind" in self.project.css_framework.lower():
                    status.update("Installing TailwindCSS 4 ...")
                    self._npm_install("tailwindcss @tailwindcss/cli")

                elif "bootstrap" in self.css_framework.lower() and self.project.framework == "django":
                    status.update("Installing django-bootstrap-v5 ...")
                    self._pip_install("django-bootstrap-v5")

            status.update(f"Starting a new [bold]{self.project.framework.capitalize()}[/bold] project...")

            # Generate the Python web framework project
            match self.project.framework:
                case "django":
                    run_command(["djangoadmin", "startproject", self.project.name])

                case "flask":
                    # Generate flask app
                    ...
                case "fast_api":
                    # Generate Fast API project
                    ...

            # Start automatic configurations
            status.update("Configuring PyBlade ...")
            self._configure_pyblade()

            if self.project.css_framework:
                if "tailwind" in self.project.css_framework.lower():
                    status.update("Configuring TailwindCSS 4 ...")
                    self._configure_tailwind()

                elif "bootstrap" in self.css_framework.lower():
                    status.update("Configuring django-bootstrap-v5 ...")
                    self._configure_bootstrap()

            status.update("Making things ready ...")
            self.success("Project created successfully.")
            self.line("Run [blue]pyblade serve[/blue] to start development server.\n")

    def _configure_pyblade(self):
        """Configures PyBlade for the project."""

        # Write the pyblade.json config file
        settings.name = self.project.name
        settings.root_dir = Path(self.project.name)
        settings.core_dir = Path(self.project.name) / self.project.name
        settings.settings_path = settings.core_dir / "settings.py"
        settings.framework.name = self.project.framework
        settings.framework.version = get_version(self.project.framework)
        settings.css_framework.name = self.project.css_framework
        settings.css_framework.version = "4" if "tailwind" in self.project.css_framework else "5"
        settings.pyblade_version = get_version()
        settings.save()

        # Create directories
        directories = [
            "templates",
            "static/css",
            "static/js",
        ]

        for directory in directories:
            Path(settings.root_dir).mkdir(parents=True, exist_ok=True)

        # Configure PyBlade in settings.py if it's a django project
        if self.project.framework == "django":
            try:
                new_temp_settings = """{
        "BACKEND": "pyblade.backends.PyBladeEngine",
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
    """
                with open(settings.settings_path, "r") as file:
                    settings = file.read()

                match = re.search(_SETTINGS_PATERN, settings)
                if match:
                    new_temp_settings = settings.replace(match.group("templates"), new_temp_settings)

                with open(settings.settings_path, "w") as file:
                    file.write(new_temp_settings)

                self.success("The template engine has been replaced with PyBlade.")
            except Exception as e:
                self.error(f"Failed to properly configure PyBlade: {str(e)}")

    def _configure_bootstrap(self):
        """Configures Bootstrap 5 for the project."""

        stubs_path = Path(__file__).parent.parent / "stubs"

        if settings.framework == "django":
            # Update settings.py
            try:
                with open(settings.settings_path, "r") as file:
                    settings = file.read()

                # Add tailwind to INSTALLED_APPS
                new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t'bootstrap5',\n")
                with open(settings.settings_path, "w") as file:
                    file.write(new_settings)

                with open(stubs_path / "bootstrap_layout.html.stub", "r") as file:
                    base_template = file.read()

                with open(settings.root_dir / "templates" / "layout.html", "w") as file:
                    file.write(base_template)

            except Exception as e:
                self.error(f"Failed to configure Bootstrap 5: {str(e)}")
                return

            self.success("Bootstrap 5 has been configured successfully.")

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""

        stubs_path = Path(__file__).parent.parent / "stubs"

        try:
            # Create the input and output static files
            with open(settings.root_dir / "static" / "css" / "input.css") as file:
                file.write('@import "tailwindcss";')

            # Create tailwind layout
            with open(stubs_path / "tailwind_layout.html.stub", "r") as file:
                base_template = file.read()

            with open(settings.root_dir / "templates" / "layout.html", "w") as file:
                file.write(base_template)

        except Exception as e:
            self.error(f"Failed to configure Tailwind: {str(e)}")
            return

        self.success("Tailwind CSS 4 has been configured successfully.")

    def _pip_install(self, package: str):
        """Installs a Python package using pip."""
        try:
            return run_command(["pip3", "install", package])
        except RunError as e:
            self.error(e.stderr)

    def _npm_install(self, package: str):
        """Installs an NPM package using npm"""
        try:
            return run_command(["npm", "install", package])
        except RunError as e:
            self.error(e.stderr)
