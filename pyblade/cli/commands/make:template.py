from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.config import settings


class Command(BaseCommand):
    """
    Create a new PyBlade template file.
    """

    name = "make:template"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        self.add_argument("name")
        self.add_flag("-f", "--force", help="Create the template even if it already exists")

    def handle(self, **kwargs):
        """Execute the 'pyblade make:template' command"""

        template_name = kwargs.get("name").split(".")

        p = Path(settings.templates_dir, *template_name[:-1])
        p.mkdir(parents=True, exist_ok=True)

        html_path = p / f"{template_name[-1]}.html"

        if html_path.exists():
            if not kwargs.get("force"):
                self.error(f"Template '{html_path}' already exists.")
                self.tip(
                    "Use [bright_black]--force[/bright_black] to override the existing "
                    "template or choose a different name."
                )
                return

        stubs_path = Path(__file__).parent.parent / "stubs"
        with open(stubs_path / "template.html.stub", "r") as file:
            template = file.read()

        with open(html_path, "w") as file:
            file.write(template)

        self.success(f"""Created template '{html_path}' successfully.""")
