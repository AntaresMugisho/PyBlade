from pathlib import Path

import questionary
from questionary import Choice
from utils.styles import PYBLADE_STYLE


class ProjectService:
    def __init__(self):
        self.project_data = self._get_project_info()

    def create_project(self):
        """Create a new PyBlade project"""
        self._create_directory_structure(project_data)
        self._install_dependencies(project_data)

    @staticmethod
    def _get_project_info():
        """Get project information from user"""
        return questionary.form(
            project_name=questionary.text("What is your project name?", default="my_project", style=custom_style),
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
