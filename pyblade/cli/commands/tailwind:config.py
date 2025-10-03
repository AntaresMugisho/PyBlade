from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.cli.exceptions import RunError
from pyblade.config import Config
from pyblade.utils import run_command


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

        self.success("Tailwind CSS 4 has been configured successfully.")

    def _configure_tailwind(self):
        """Configures Tailwind CSS for the project."""

        stubs_path = Path(__file__).parent.parent / "stubs"

        css_static_dir = Path("static") / "css"
        css_static_dir.mkdir(parents=True, exist_ok=True)

        templates_dir = Path("templates")
        templates_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Create the input and output static files
            with open(css_static_dir / "input.css", "w") as file:
                file.write('@import "tailwindcss";')

            # Create tailwind layout
            with open(stubs_path / "tailwind_layout.html.stub", "r") as file:
                base_template = file.read()

            with open(templates_dir / "layout.html", "w") as file:
                file.write(base_template)

        except Exception as e:
            self.error(f"Failed to configure Tailwind: {str(e)}")
            return

    def _npm_install(self, package: str):
        """Installs an NPM package using npm"""
        try:
            return run_command(["npm", "install", package], self.settings.root_dir)
        except RunError as e:
            self.error(e.stderr)
