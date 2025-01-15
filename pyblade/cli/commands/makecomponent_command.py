from pathlib import Path

from ..commands.base_command import BaseCommand


class MakeComponentCommand(BaseCommand):
    name = "make:component"
    description = "Create a new PyBlade component"
    arguments = ["name"]

    def handle(self, **kwargs):
        """Create a new component in the templates directory."""
        component_name = kwargs.get("name")
        templates_dir = self.settings.pyblade_root / Path(self.settings.project_name) / "templates"
        components_dir = templates_dir / "components"

        # Ensure templates directory exists
        if not components_dir.exists():
            components_dir.mkdir(parents=True)

        # Create component path
        component_path = components_dir / f"{component_name}.html"

        if component_path.exists():
            self.error(f"Component '{component_name}' already exists at {component_path}")
            overwrite = self.confirm("Do you want to overwrite it?", default=False)
            if not overwrite:
                return

        # Create component with template
        with open(component_path, "w") as f:
            f.write(
                """@props({})

<div>
    {# Component content goes here #}
</div>
"""
            )
        self.info(f"Component created successfully at '{component_path}'")
