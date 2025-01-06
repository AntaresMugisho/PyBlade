import os
import subprocess
import time
from pathlib import Path

import questionary
from commands.base_command import BaseCommand
from questionary import Choice
from utils.console import console
from utils.styles import PYBLADE_STYLE


class InitCommand(BaseCommand):
    name = "init"
    description = "Create a new PyBlade project"

    def handle(self, **kwargs):
        # Get project configuration
        self.project_data = self._get_project_info()

        if not self.project_data:
            return

        # Confirm project details
        console.print(
            f"""
            Project details :
                - Project name : [bold]{self.project_data['project_name']}[/bold]
                - Framework : [bold]{self.project_data['framework']}[/bold]
                - CSS framework : [bold]{self.project_data['css_framework'] or 'None'}[/bold]
                - Use LiveBlade : [bold]{'Yes' if self.project_data['use_liveblade'] else 'No'}[/bold]
            """
        )

        if not questionary.confirm("Is this correct?").ask():
            self.error("Project creation cancelled.")
            return

        with console.status("[blue]Installing dependencies...[/blue]\n\n") as status:
            self._install_dependencies()

            status.update(f"[blue]Starting a new [bold]{self.project_data['framework']}[/bold] project...[/blue]")
            subprocess.check_call(["django-admin", "startproject", self.project_data["project_name"]])

            status.update("[blue]Configuring PyBlade Template Engine...[/blue]\n\n")
            self._configure_pyblade()

            if self.project_data["use_liveblade"]:
                status.update("[blue]Configuring LiveBlade...[/blue]\n\n")
                self._configure_liveblade()

            if "tailwind" in self.project_data["css_framework"].lower():
                status.update("[blue]Configuring Tailwind CSS...[/blue]\n\n")
                self._configure_tailwind()

            elif "bootstrap" in self.project_data["css_framework"].lower():
                status.update("[blue]Configuring Bootstrap 5...[/blue]\n\n")
                self._configure_bootstrap()

            self.success("Pyblade Project created successfully !")

    @staticmethod
    def _get_project_info():
        """Get project information from user"""
        return questionary.form(
            project_name=questionary.text("hat is your project name?", default="my_project", style=PYBLADE_STYLE),
            framework=questionary.select(
                "Which Python web framework would you like to use?",
                choices=["Django", "Flask"],
                style=PYBLADE_STYLE,
            ),
            css_framework=questionary.select(
                "Would you like to install a CSS framework?",
                choices=["Tailwind CSS", "Bootstrap 5", Choice("Not sure", False)],
                style=PYBLADE_STYLE,
            ),
            use_liveblade=questionary.select(
                "Would you like to use LiveBlade for interactive UI?",
                choices=[Choice("Yes", True), Choice("No", False)],
                style=PYBLADE_STYLE,
            ),
        ).ask()

    def _install_dependencies(self):
        """Install project dependencies based on configuration"""

        # Install framework-specific dependencies
        if self.project_data["framework"].lower() == "django":
            self._pip_install("django")

        elif self.project_data["framework"].lower() == "flask":
            self._pip_install("flask")

        # Install CSS framework-specific dependencies
        if "tailwind" in self.project_data["css_framework"].lower():
            self._pip_install("django-tailwind[reload]")

        elif "bootstrap" in self.project_data["css_framework"].lower():
            self._pip_install("django-bootstrap-v5")

    def _configure_pyblade(self):
        """Configures PyBlade for the Django project."""

        # Create directory structure
        project_path = Path(self.project_data["project_name"])

        directories = [
            "templates",
            "components",
            "static/css",
            "static/js",
        ]

        for directory in directories:
            (project_path / directory).mkdir(parents=True, exist_ok=True)

        # Configure PyBlade in settings.py if it's a django project
        if self.project_data["framework"].lower() == "django":
            settings_path = project_path / project_path / "settings.py"
            try:
                with open(settings_path, "r") as file:
                    settings = file.read()

                new_settings = settings.replace("'DIRS': [],", "'DIRS': [BASE_DIR / 'templates'],").replace(
                    "'django.template.backends.django.DjangoTemplates',", "'pyblade.backends.DjangoPyBlade',"
                )

                with open(settings_path, "w") as file:
                    file.write(new_settings)

                self.success("The template engine has been replaced with PyBlade.")
            except Exception as e:
                self.error(f"{str(e)}")
                return

            # Change default welcome file
            try:
                with open("templates/default_urlconf.html", "r") as file:
                    default_urlconf = file.read()

                for root, _, files in os.walk("."):
                    if "default_urlconf.html" in files:
                        with open(f"{root}/default_urlconf.html", "w", encoding="utf-8") as file:
                            file.write(default_urlconf)

            except Exception as e:
                self.error(f"{str(e)}")
                return

    def _configure_liveblade(self):
        """Configures LiveBlade for the project."""
        time.sleep(3)
        self.success("LiveBlade has been installed successfully.")

    def _configure_bootstrap(self):
        """Configures Bootstrap 5 for the project."""
        project_path = Path(self.project_data["project_name"])

        if self.project_data["framework"].lower() == "django":
            # Update settings.py
            settings_path = project_path / self.project_data["project_name"] / "settings.py"
            try:
                with open(settings_path, "r") as file:
                    settings = file.read()

                # Add bootstrap5 to INSTALLED_APPS
                new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'bootstrap5',")

                with open(settings_path, "w") as file:
                    file.write(new_settings)

                # Create base template with Bootstrap
                templates_dir = project_path / "templates"
                templates_dir.mkdir(exist_ok=True)

                base_template = """"""

                with open(templates_dir / "base.html", "w") as file:
                    file.write(base_template)

            except Exception as e:
                self.error(f"Failed to configure Bootstrap: {str(e)}")
                return

        self.success("Bootstrap 5 has been configured successfully.")

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""
        project_path = Path(self.project_data["project_name"])

        if self.project_data["framework"].lower() == "django":
            # Update settings.py
            settings_path = project_path / self.project_data["project_name"] / "settings.py"
            try:
                with open(settings_path, "r") as file:
                    settings = file.read()

                # Add tailwind to INSTALLED_APPS
                new_settings = settings.replace(
                    "INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'tailwind',\n    'theme',"
                )

                with open(settings_path, "w") as file:
                    file.write(new_settings)

                # Add Tailwind app name
                new_settings += "\n\nTAILWIND_APP_NAME = 'theme'\n\nINTERNAL_IPS = ['127.0.0.1']"

                with open(settings_path, "w") as file:
                    file.write(new_settings)

                # Create theme app
                subprocess.check_call(["python", "manage.py", "tailwind", "init", "--no-input"], cwd=project_path)
                subprocess.check_call(["python", "manage.py", "tailwind", "install"], cwd=project_path)

                # Create base template
                templates_dir = project_path / "templates"
                templates_dir.mkdir(exist_ok=True)

                base_template = """"""

                with open(templates_dir / "base.html", "w") as file:
                    file.write(base_template)

            except Exception as e:
                self.error(f"Failed to configure Tailwind: {str(e)}")
                return

            self.success("Tailwind CSS has been configured successfully.")
            self.info("To start the Tailwind CSS build process, run 'pyblade tailwind:start'")

    def _pip_install(self, package: str):
        """Installs a Python package using pip."""
        try:
            subprocess.check_call(["pip3", "install", package])
        except Exception as e:
            raise e
