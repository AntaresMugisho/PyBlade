from pathlib import Path

from ..commands.base_command import BaseCommand


class MakeComponentCommand(BaseCommand):
    name = "make:component"
    description = "Create a new PyBlade component"
    arguments = ["name"]

    def handle(self, **kwargs):
        """Create a new component."""

        dst = Path(kwargs.get("name"))
        if dst.exists():
            self.error(f"Component '{dst}' already exists.")
            return

        with open(dst, "w") as f:
            f.write(
                """
@props({})

<div>
   {# slot #}
</div>
            """
            )
        self.info(f"Creating component '{dst}'")
