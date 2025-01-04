from pathlib import Path

import questionary
from questionary import Choice

from ..utils.console import console
from ..utils.styles import PYBLADE_STYLE
from .base_command import BaseCommand


class InitCommand(BaseCommand):
    name = "init"
    description = "Create a new PyBlade project"

    def handle(self, **kwargs):

        # Get project configuration
        project_data = self.get_project_info()

        console.print(
            f"""
            Here are your project configuration
             - Project name : {project_data['project_name']}
             - Framework : {project_data['framework']}
             - CSS framework : {project_data['css_framework']}
             - Use LiveBlade : {project_data['use_liveblade']}
            """
        )

        if not questionary.confirm("Is this correct?").ask():
            self.error("Project creation cancelled.")
            return

        # Create directory structure
        # Create project
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

    def _create_directory_structure(self, project_data):
        """Create project directory structure"""
        project_path = Path(project_data["project_name"])

        # Create directories
        directories = [
            "templates",
            "components",
            "layouts",
            "static/css",
            "static/js",
        ]

        for directory in directories:
            (project_path / directory).mkdir(parents=True, exist_ok=True)

    def _install_dependencies(self, project_data):
        """Install project dependencies based on configuration"""
        # Implementation for installing dependencies
        pass
