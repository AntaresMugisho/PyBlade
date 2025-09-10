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

    def handle(self, **kwargs):
        """Execute the 'pyblade make:template' command"""

        templates_path = Path(settings.templates_dir)
        stubs_path = Path(__file__).parent.parent / "stubs"

        template_name = kwargs.get("name").split(".")

        p = Path(templates_path, *template_name[:-1])
        p.mkdir(parents=True, exist_ok=True)

        with open(stubs_path / "template.html.stub", "r") as file:
            template = file.read()

        with open(p / f"{template_name[-1]}.html", "w") as file:
            file.write(template)

        self.success(f"""Created template '{p / f"{template_name[-1]}.html"}' successfully.""")
