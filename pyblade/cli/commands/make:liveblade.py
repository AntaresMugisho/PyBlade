from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.config import settings
from pyblade.utils import pascal_to_snake, snakebab_to_pascal, split_dotted_path


class Command(BaseCommand):
    """
    Create a new Liveblade component.
    """

    name = "make:liveblade"

    def config(self):
        """Setup command arguments and options here"""
        self.add_argument("name")
        self.add_flag("-i", "--inline", help="Embed the HTML template in the Python component class file")
        self.add_flag("-f", "--force", help="Create the Liveblade component even if it already exists")

    def handle(self, **kwargs):
        """Create a new Liveblade component."""

        name = pascal_to_snake(kwargs.get("name"))
        path, component_name = split_dotted_path(name)

        components_dir = Path(settings.liveblade.components_dir / path)
        templates_dir = Path(settings.templates_dir, settings.liveblade.templates_dir / path)

        # Ensure liveblade directories exist
        components_dir.mkdir(parents=True, exist_ok=True)
        templates_dir.mkdir(parents=True, exist_ok=True)

        # Create component path
        html_file = templates_dir / f"{component_name}.html"
        python_file = components_dir / f"{component_name}.py"

        # Check for existing files
        if html_file.exists() or python_file.exists():
            if not kwargs.get("force"):
                self.error(f"Component '{component_name}' already exists at {python_file}")
                self.tip(
                    "Use [bright_black]--force[/bright_black] to override the existing "
                    "component or choose a different name."
                )
                return

        stubs_dir = settings.stubs_dir / "liveblade"

        if not kwargs.get("inline"):
            python_stub = stubs_dir / "component.py.stub"
            html_stub = stubs_dir / "template.html.stub"

            if not python_stub.exists():
                self.error("Python stub not found.")
                return

            if not html_stub.exists():
                self.error("HTML stub not found.")
                return

            # Create HTML template
            with open(html_stub, "r") as file:
                html_template = file.read()

            with open(html_file, "w") as file:
                file.write(html_template)

        else:
            python_stub = stubs_dir / "inline_component.py.stub"

        # Create Python component
        with open(python_stub, "r") as file:
            python_template = file.read()
            python_template = python_template.format(
                class_name=snakebab_to_pascal(component_name), template_name=html_file
            )

        with open(python_file, "w") as file:
            file.write(python_template)

        self.success("Liveblade component created successfully:")
        self.line(f"  - Python: {python_file}")
        if not kwargs.get("inline"):
            self.line(f"  - HTML: {html_file}")
