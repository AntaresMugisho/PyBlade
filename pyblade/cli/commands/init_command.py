import subprocess
from pathlib import Path
import os

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

        with console.status("Installing dependencies...") as status:
            self._install_dependencies()

            status.update(f"Starting a new {self.project_data['framework']} project...")
            subprocess.check_call(["django-admin", "startproject", self.project_data["project_name"]])

            status.update("Configuring PyBlade Template Engine...")
            self._configure_pyblade

            if self.project_data["use_liveblade"]:
                status.update("Configuring LiveBlade...")
                self._configure_liveblade()

            if "tailwind" in self.project_data["css_framework"].lower():
                status.update("Configuring Tailwind CSS...")
                self._configure_tailwind()

            elif "bootstrap" in self.project_data["css_framework"].lower():
                status.update("Configuring Bootstrap 5...")
                self._configure_bootstrap()

            status.success("✨ Pyblade Project created successfully !")

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
            self._pip_install("django-tailwind")

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
            settings_path = project_path / project_name / "settings.py"
            try:
                with open(settings_path, "r") as file:
                    settings = file.read()

                new_settings = settings.replace("'DIRS': [],", "'DIRS': [BASE_DIR / templates')],").replace(
                    "'django.template.backends.django.DjangoTemplates',", "'pyblade.backends.DjangoPyBlade',"
                )

                with open(settings_path, "w") as file:
                    file.write(new_settings)

                console.print("✔️ The template engine has been replaced with PyBlade.")
            except Exception as e:
                console.print(f"❌ 'settings.py' file not found in {settings_path}.")
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
                console.print(f"❌ {str(e)}")

    def _configure_liveblade(self):
        """Configures LiveBlade for the project."""
        pass

    def _configure_bootstrap(self):
        """Configures Bootstrap 5 for the project."""
        pass

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""
        pass

    def _pip_install(self, package: str):
        """Installs a Python package using pip."""
        try:
            subprocess.check_call(["pip3", "install", package])
        except Excepetion as e:
            raise e
