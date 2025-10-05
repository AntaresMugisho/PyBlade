import re
from pathlib import Path

from questionary import Choice

from pyblade.cli import BaseCommand
from pyblade.cli.exceptions import RunError
from pyblade.config import Config
from pyblade.utils import get_version, run_command

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
        try:
            self.project = self.form(
                name=self.ask("What is your project name ?", default="my_project"),
                framework=self.choice(
                    "Which Python web framework would you like to use?",
                    choices=[Choice("Django", "django"), Choice("Flask", "flask")],
                ),
                css_framework=self.choice(
                    "Would you like to configure a CSS framework?",
                    choices=["TailwindCSS 4", "Bootstrap 5", Choice("Not sure", False)],
                ),
            )
        except KeyboardInterrupt:
            self.info("Aborted by user !")
            return

        else:
            # Ensure there is no other project with the same name
            if Path(self.project.name).exists():
                self.error(
                    f"A project with the name '{self.project.name}' already exists."
                    " Consider choosing a different name for your new project."
                )
                return

            # Confirm project details
            self.line(
                f"""
    Project details :
        - Project name : [bold]{self.project.name}[/bold]
        - Framework : [bold]{self.project.framework.capitalize()}[/bold]
        - CSS framework : [bold]{self.project.css_framework or 'None'}[/bold]
    """
            )

            if not self.confirm("Is this correct?", True):
                self.info("Aborted by user.")
                return

            # Generate project
            with self.status("Installing Python dependencies ...") as status:
                # Install python web framework
                self._pip_install(self.project.framework)

                status.update(f"Starting a new [bold]{self.project.framework.capitalize()}[/bold] project...\n")

                # Generate the Python web framework project
                match self.project.framework:
                    case "django":
                        try:
                            run_command(f"django-admin startproject {self.project.name}")
                        except RunError as e:
                            self.error(str(e))
                            return

                    case "flask":
                        # Generate flask app
                        ...

                    case "fastapi":
                        # Generate Fast API project
                        ...

                # Start automatic configurations
                status.update("Configuring PyBlade ...")
                self._configure_pyblade()

                if self.project.css_framework:
                    # Install and Configure CSS Framework
                    if "tailwind" in self.project.css_framework.lower():
                        status.update("Installing TailwindCSS 4 ...")
                        self._npm_install("tailwindcss")
                        self._npm_install("@tailwindcss/cli")

                        status.update("Configuring TailwindCSS 4 ...")
                        self._configure_tailwind()

                    elif "bootstrap" in self.css_framework.lower() and self.project.framework == "django":
                        status.update("Installing django-bootstrap-v5 ...")
                        self._pip_install("django-bootstrap-v5")

                        status.update("Configuring django-bootstrap-v5 ...")
                        self._configure_bootstrap()

                status.update("Making things ready ...")
                self.success("Project created successfully.")
                self.line("Run [blue]pyblade serve[/blue] to start a development server.\n")

    def _configure_pyblade(self):
        """Configures PyBlade for the project."""

        self.settings = Config(config_file=Path(self.project.name, "pyblade.json"))

        self.settings.name = self.project.name
        self.settings.core_dir = self.project.name
        self.settings.settings_path = f"{self.settings.core_dir}/settings.py"
        self.settings.framework = self.project.framework
        self.settings.css_framework = self.project.css_framework
        self.settings.pyblade_version = get_version()
        self.settings.save()

        # Update without saving to prevent absolute path in a file that might be pubished
        # on a different server

        self.settings.root_dir = Path(self.project.name)
        self.settings.settings_path = self.settings.root_dir / self.settings.core_dir / "settings.py"

        # Create directories
        directories = [
            "templates",
            "static/css",
            "static/js",
        ]

        for directory in directories:
            Path(self.settings.root_dir, directory).mkdir(parents=True, exist_ok=True)

        # Configure PyBlade in settings.py if it's a django project
        if self.project.framework == "django":
            try:
                new_temp_settings = """{
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
        },"BACKEND": "pyblade.backends.PyBladeEngine",
    },
    """
                with open(self.settings.settings_path, "r") as file:
                    settings = file.read()

                match = re.search(_SETTINGS_PATERN, settings)
                if match:
                    new_temp_settings = settings.replace(match.group("templates"), new_temp_settings)

                with open(self.settings.settings_path, "w") as file:
                    file.write(new_temp_settings)

                self.success("The template engine has been replaced with PyBlade.")
            except Exception as e:
                self.error(f"Failed to properly configure PyBlade: {str(e)}")

    def _configure_bootstrap(self):
        """Configures Bootstrap 5 for the project."""

        stubs_path = Path(__file__).parent.parent / "stubs"

        if self.settings.framework == "django":
            # Update settings.py
            try:
                with open(self.settings.settings_path, "r") as file:
                    settings = file.read()

                # Add tailwind to INSTALLED_APPS
                new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t'bootstrap5',\n")
                with open(self.settings.settings_path, "w") as file:
                    file.write(new_settings)

                with open(stubs_path / "bootstrap_layout.html.stub", "r") as file:
                    base_template = file.read()

                with open(self.settings.root_dir / "templates/layout.html", "w") as file:
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
            with open(self.settings.root_dir / "static/css/input.css") as file:
                file.write('@import "tailwindcss";')

            # Create tailwind layout
            with open(stubs_path / "tailwind_layout.html.stub", "r") as file:
                base_template = file.read()

            with open(self.settings.root_dir / "templates/layout.html", "w") as file:
                file.write(base_template)

        except Exception as e:
            self.warning(f"Failed to configure Tailwind: {str(e)}")
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
            return run_command(["npm", "install", package], self.settings.root_dir)
        except RunError as e:
            self.error(e.stderr)
