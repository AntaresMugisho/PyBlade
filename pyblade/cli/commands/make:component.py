from pathlib import Path

from pyblade.cli import BaseCommand
from pyblade.config import settings
from pyblade.utils import pascal_to_snake, split_dotted_path


class Command(BaseCommand):
    """
    Create a new PyBlade component file.
    """

    name = "make:component"

    def config(self):
        """Setup command arguments and options here"""
        self.add_argument("name")
        self.add_flag("-f", "--force", help="Create the component even if it already exists")

    def handle(self, **kwargs):
        """Create a new component in the templates directory."""
        name = pascal_to_snake(kwargs.get("name"))
        path, component_name = split_dotted_path(name)

        if not path and component_name == "slot":
            self.error("You are not allowed to create a 'slot' component at the root level.")
            return

        components_dir = Path(settings.templates_dir, settings.components_dir, path)
        components_dir.mkdir(parents=True, exist_ok=True)

        component_file = components_dir / f"{component_name}.html"

        if component_file.exists():
            self.error(f"Component '{component_name}' already exists at {component_file}")
            self.tip(
                "Use [bright_black]--force[/bright_black] to override the existing "
                "component or choose a different name."
            )
            return

        html_stub = settings.stubs_dir / "component.html.stub"
        if not html_stub.exists():
            self.error("Component stub not found.")
            return

        with open(html_stub, "r") as file:
            component_template = file.read()

        with open(component_file, "w") as f:
            f.write(component_template)

        self.success(f"Component created successfully at '{component_file}'")
