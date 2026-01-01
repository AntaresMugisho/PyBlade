from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.cli.exceptions import CommandError
from pyblade.config import Config
from pyblade.utils import run_command, get_project_root


class Command(BaseCommand):
    """
    Install and configure TailwindCSS 4 in the current project.
    """

    name = "tailwind:config"
    aliases = ["tw:config"]  # Other possible names for the command

    def handle(self, **kwargs):
        """Execute the 'pyblade tailwind:config' command"""
        self.settings = Config(config_file="pyblade.json")

        self.settings.css_framework = "TailwindCSS 4"

        with self.status("Installing Tailwind CSS 4...") as status:
            self._npm_install("tailwindcss")
            self._npm_install("@tailwindcss/cli")

            status.update("Configuring Tailwind CSS 4...")
            self._configure_tailwind()

        self.settings.save()

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""

        stubs_path = self.settings.stubs_dir
        root_dir = get_project_root()

        input_css = root_dir / "static/css/input.css"
        input_css.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Create the input and output static files
            with open(input_css, "w") as file:
                file.write('@import "tailwindcss";')

            # Create tailwind layout
            with open(stubs_path / "tailwind_layout.html.stub", "r") as file:
                base_template = file.read()

            with open(root_dir / "templates/layout.html", "w") as file:
                file.write(base_template)

        except Exception as e:
            self.warning(f"Failed to configure Tailwind: {str(e)}")
            return

        self.success("Tailwind CSS 4 has been configured successfully.")


    def _npm_install(self, package: str):
        """Installs an NPM package using npm"""
        try:
            return run_command(["npm", "install", package], get_project_root())
        except CommandError as e:
            self.error(e.stderr)
