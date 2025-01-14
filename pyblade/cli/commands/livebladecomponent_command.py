from pathlib import Path

from ..commands.base_command import BaseCommand


class LivebladeComponentCommand(BaseCommand):
    name = "liveblade:component"
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

        templates_dir = Path("templates")
        liveblade_dir = templates_dir / "liveblade"
        components_dir = Path("components")

        # Ensure liveblade directory exists
        if not liveblade_dir.exists():
            liveblade_dir.mkdir(parents=True)

        # Ensure components directory exists
        if not components_dir.exists():
            components_dir.mkdir(parents=True)

        # Create component path
        component_path = components_dir / f"{component_name}.html"
        html_file = liveblade_dir / f"{component_name}.html"
        python_file = components_dir / f"{component_name}.py"
        # Check for existing files
        if component_path.exists():
            if component_path.exists():
            self.error(f"Component '{component_name}' already exists at {component_path}")
            overwrite = self.confirm("Do you want to overwrite it?", default=False)
            if not overwrite:
                return
            self.error(f"HTML component '{component_name}' already exists at {html_file}")
            return

        if python_file.exists():
            self.error(f"Python component '{component_name}' already exists at {python_file}")
            return

        # Create HTML template
        with open(html_file, "w") as f:
            f.write("""<div>
    {# Component content goes here #}
</div>
"""
        )

        # Create Python file with state management if requested
        with open(python_file, "w") as f:
            f.write(f'''
from pyblade import liveblade

class {component_name.title()}Component(liveblade.Component):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


    def render(self):
        """Called when component is mounted"""
        return liveblade.view("{component_name}", context={{}})
''')

        self.info(f"LiveBlade component created successfully:")
        self.info(f"  - HTML: {html_file}")
        self.info(f"  - Python: {python_file}")
