from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.config import settings
from pyblade.utils import split_dotted_path


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

        name = kwargs.get("name")
        path, template_name = split_dotted_path(name)

        p = Path(settings.templates_dir, path)
        p.mkdir(parents=True, exist_ok=True)

        html_path = p / f"{template_name}.html"

        if html_path.exists():
            if not kwargs.get("force"):
                self.error(f"Template '{html_path}' already exists.")
                self.tip(
                    "Use [bright_black]--force[/bright_black] to override the existing "
                    "template or choose a different name."
                )
                return

        stubs_path = settings.stubs_dir / "templates"
        template_stub = stubs_path / "template.html.stub"

        if not template_stub.exists():
            self.error("Template stub not found.")
            return

        with open(template_stub, "r") as file:
            template = file.read()

        with open(html_path, "w") as file:
            file.write(template)

        self.success(f"""Created template '{html_path}' successfully.""")
