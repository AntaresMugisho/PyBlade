import re
import time
from pathlib import Path

from questionary import Choice

from pyblade.cli import BaseCommand
from pyblade.cli.exceptions import RunError
from pyblade.cli.utils import run_command

# from pyblade.config import settings


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

        # Get project configuration
        self.project_name = self.ask(
            "What is your project name?",
            default="my_project",
        )

        self.framework = self.choice(
            "Which Python web framework would you like to use?",
            choices=[Choice("Django", "django")],
        )

        self.css_framework = self.choice(
            "Would you like to configure a CSS framework?",
            choices=["Tailwind 4", "Bootstrap 5", Choice("Not sure", False)],
        )

        self.use_liveblade = self.confirm(
            "Would you like to use Liveblade?",
        )

        # Extract important project data
        self.root_dir = Path(self.project_name)
        self.core_dir = Path(self.project_name) / self.project_name
        self.settings_dir = self.core_dir / "settings.py"
        self.cli_path = Path(__file__).parent.parent

        # Confirm project details
        self.line(
            f"""
Project details :
    - Project name : [bold]{self.project_name}[/bold]
    - Framework : [bold]{self.framework}[/bold]
    - CSS framework : [bold]{self.css_framework or 'None'}[/bold]
    - Use Liveblade : [bold]{'Yes' if self.use_liveblade else 'No'}[/bold]
"""
        )

        if not self.confirm("Is this correct?"):
            self.info("Project creation cancelled.")
            return

        # Generate project
        with self.status("[blue]Creating a PyBlade-powered project...[/blue]\n\n") as status:
            self._install_dependencies()

            status.update(f"[blue]Starting a new [bold]{self.framework}[/bold] project...[/blue]")
            status.update("Starting a new django project...")
            time.sleep(2)
            self.check("Starting a new django project")

            status.update("Configuring django project...")
            time.sleep(2)
            self.check("Configuring django project")

            status.update("Installing tailwind CSS 4...")
            time.sleep(2)
            self.check("Installing tailwind CSS 4")

            status.update("Configuring tailwind CSS 4...")
            time.sleep(2)
            self.check("Configuring tailwind CSS 4")

            status.update("Configuring Liveblade")
            time.sleep(3)
            self.check("Done")

            status.update("Final touches...")
            time.sleep(3)
            self.success("Project created successfully.")
            self.line("Run [blue]pyblade serve[/blue] to start a development server.\n")
            # try:
            #     run_command(["django-admin", "startproject", self.project_name])
            # except RunError as e:
            #     self.error(e.stderr or "Read the traceback for more information")
            #     return

            # status.update("[blue]Configuring PyBlade Template Engine...[/blue]\n\n")
            # self._configure_pyblade()

            # if self.use_liveblade:
            #     status.update("[blue]Configuring LiveBlade...[/blue]\n\n")
            #     self._configure_liveblade()

            # if self.css_framework:
            #     if "tailwind" in self.css_framework.lower():
            #         status.update("[blue]Configuring Tailwind CSS...[/blue]\n\n")
            #         self._configure_tailwind()

            #     elif "bootstrap" in self.css_framework.lower():
            #         status.update("[blue]Configuring Bootstrap 5...[/blue]\n\n")
            #         self._configure_bootstrap()

            # self.settings.pyblade_root = Path(self.project_name)
            # self.pyblade_settings = {
            #     "name": self.project_name,
            #     "framework": self.framework,
            #     "css_framework": self.css_framework or None,
            #     "pyblde_version": __version__,
            # }

            # self.settings.serialize(self.pyblade_settings)

            # self.success("Pyblade Project created successfully !")

    def _install_dependencies(self):
        """Install project dependencies based on configuration"""

        # Install framework-specific dependencies
        if self.framework.lower() == "django":
            self._pip_install("django")

        elif self.framework.lower() == "flask":
            self._pip_install("flask")

        # Install CSS framework-specific dependencies
        if self.css_framework:
            if "tailwind" in self.css_framework.lower():
                self._pip_install("django-tailwind[reload]")

            elif "bootstrap" in self.css_framework.lower():
                self._pip_install("django-bootstrap-v5")

    def _configure_pyblade(self):
        """Configures PyBlade for the Django project."""

        # Add directories
        directories = [
            "templates",
            "static/css",
            "static/js",
        ]

        for directory in directories:
            Path(self.default_app_path / directory).mkdir(parents=True, exist_ok=True)

        # Configure PyBlade in settings.py if it's a django project

        if self.framework.lower() == "django":
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

                with open(self.settings_path, "r") as file:
                    settings = file.read()

                match = re.search(_SETTINGS_PATERN, settings)
                if match:
                    new_temp_settings = settings.replace(match.group("templates"), new_temp_settings)

                with open(self.settings_path, "w") as file:
                    file.write(new_temp_settings)

                self.success("The template engine has been replaced with PyBlade.")
            except Exception as e:
                self.error(f"Failed to configure PyBlade: {str(e)}")
                return

    def _configure_liveblade(self):
        """Configures LiveBlade for the project."""

        Path(self.default_app_path / "components").mkdir(parents=True, exist_ok=True)
        Path(self.default_app_path / "templates" / "liveblade").mkdir(parents=True, exist_ok=True)

        self.success("LiveBlade has been installed successfully.")

    def _configure_bootstrap(self):
        """Configures Bootstrap 5 for the project."""

        if self.framework.lower() == "django":
            # Update settings.py
            try:
                with open(self.settings_path, "r") as file:
                    settings = file.read()

                # Add tailwind to INSTALLED_APPS
                new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t'bootstrap5',\n")
                with open(self.settings_path, "w") as file:
                    file.write(new_settings)

                with open(self.cli_path / "templates/bootstrap_layout.html", "r") as file:
                    base_template = file.read()

                with open(self.default_app_path / "templates" / "layout.html", "w") as file:
                    file.write(base_template)

            except Exception as e:
                self.error(f"Failed to configure Bootstrap 5: {str(e)}")
                return

            self.success("Bootstrap 5 has been configured successfully.")

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""

        if self.framework.lower() == "django":
            # Update settings.py
            try:
                with open(self.settings_path, "r") as file:
                    settings = file.read()

                # Add tailwind to INSTALLED_APPS
                new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t'tailwind',")
                new_settings += "\nTAILWIND_APP_NAME = 'theme'\n\nINTERNAL_IPS = ['127.0.0.1']"
                with open(self.settings_path, "w") as file:
                    file.write(new_settings)

                # Create tailwind layout
                with open(self.cli_path / "templates/tailwind_layout.html", "r") as file:
                    base_template = file.read()

                with open(self.default_app_path / "templates" / "layout.html", "w") as file:
                    file.write(base_template)

                try:
                    # Create theme app
                    run_command(["python", "manage.py", "tailwind", "init", "--no-input"], cwd=Path(self.project_name))
                    self.line("\tTailwind application 'theme' has been successfully created.")

                    # Add the theme app to settings.py
                    with open(self.settings_path, "r") as file:
                        settings = file.read()

                    new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n\t'theme',")
                    with open(self.settings_path, "w") as file:
                        file.write(new_settings)

                    # Install tailwind
                    run_command(["python", "manage.py", "tailwind", "install"], cwd=Path(self.project_name))
                except RunError as e:
                    self.error(
                        f"Failed to configure Tailwind: {str(e.stderr)}\n"
                        "Please Configure manually by running 'pyblade tailwind:init'"
                        " and 'pyblade tailwind:install'"
                    )
                    return

            except Exception as e:
                self.error(f"Failed to configure Tailwind: {str(e)}")
                return

        self.success("Tailwind CSS has been configured successfully.")

    def _pip_install(self, package: str):
        """Installs a Python package using pip."""
        try:
            run_command(["pip3", "install", package])
        except RunError as e:
            self.error(e.stderr)
