from pathlib import Path

from ..commands.base_command import BaseCommand


class MakeLivebladeCommand(BaseCommand):
    name = "make:liveblade"
    description = "Create a new LiveBlade component"
    arguments = ["name"]
    options = {
        "name": {
            "help": "Name of the component",
            "default": "liveblade",
        },
    }

    def handle(self, **kwargs):
        """Create a new LiveBlade component."""
        component_name = kwargs.get("name")

        templates_dir = self.settings.pyblade_root / Path(self.settings.project_name) / "templates"
        liveblade_dir = templates_dir / "liveblade"
        components_dir = Path(self.settings.pyblade_root) / "liveblade"

        # Ensure liveblade directory exists
        if not liveblade_dir.exists():
            liveblade_dir.mkdir(parents=True)

        # Ensure components directory exists
        if not components_dir.exists():
            components_dir.mkdir(parents=True)

        # Create component path
        html_file = liveblade_dir / f"{component_name}.html"
        python_file = components_dir / f"{component_name}.py"

        # Check for existing files
        if html_file.exists() or python_file.exists():
            self.warning(f"Component '{component_name}' already exists at {html_file}")
            overwrite = self.confirm("Do you want to overwrite it?", default=False)
            if not overwrite:
                return

        # Create HTML template
        with open(html_file, "w") as f:
            f.write(
                """<div>
    {# Component content goes here #}
</div>
"""
            )

        # Create Python file
        with open(python_file, "w") as f:
            f.write(
                f"""from pyblade import liveblade

class {component_name.title()}Component(liveblade.Component):

    def render(self):
        # Render liveblade/{component_name}.html

        return self.view(context={{}})
"""
            )

        self.success("LiveBlade component created successfully:")
        self.line(f"  - HTML: {html_file}")
        self.line(f"  - Python: {python_file}")
        self.newline()
