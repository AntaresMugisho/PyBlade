import subprocess
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
        self.project_data = self.get_project_info()

        if not project_data:
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

        self.info("Creating project structure...")

        # Configure project
        self.info("Configuring project...")

        # self.success(f"Project {project_data['name']} created successfully!")

        # Install dependencies
        self.info("Installing dependencies...")
        self._install_dependencies(project_data)

        self.success("Dependencies installed successfully!")

    @staticmethod
    def get_project_info():
        """Get project information from user"""
        return questionary.form(
            project_name=questionary.text("What is your project name?", default="my_project", style=PYBLADE_STYLE),
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

    def _create_directory_structure(self):
        """Create project directory structure"""

        project_path = Path(self.project_data["project_name"])

        # Create directories
        directories = [
            "templates",
            "components",
            "layouts",
            "static/css",
            "static/js",
        ]

        # for directory in directories:
        #     (project_path / directory).mkdir(parents=True, exist_ok=True)

    def _install_dependencies(self):
        """Install project dependencies based on configuration"""

        # Install framework-specific dependencies
        if self.project_data["framework"].lower() == "django":
            subprocess.check_call(["pip", "install", "django"])
        elif self.project_data["framework"].lower() == "flask":
            subprocess.check_call(["pip", "install", "flask"])

        # Install CSS framework-specific dependencies
        if self.project_data["css_framework"].lower().conains("tailwind"):
            subprocess.check_call(["pip", "install", "django-tailwind"])
        elif self.project_data["css_framework"].lower().contains("bootstrap"):
            subprocess.check_call(["pip", "install", "django-bootstrap-v5"])
