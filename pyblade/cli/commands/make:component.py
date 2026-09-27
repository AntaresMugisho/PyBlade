import importlib

from pyblade.cli import BaseCommand
from pyblade.cli.locations import LocationError, shown, target_directory
from pyblade.config import config
from pyblade.utils import pascal_to_snake, split_dotted_path


class Command(BaseCommand):
    """
    Create a new PyBlade component file.
    """

    name = "make:component"

    def config(self):
        """Setup command arguments and options here"""
        self.add_argument("name")
        self.add_option("-a", "--app", help="Create it in the components of this Django app, instead of the project's")
        self.add_flag("-l", "--live", help="Create a pyblade live component")
        self.add_flag("-i", "--inline", help="Create a template-less live component")
        self.add_flag("-f", "--force", help="Create the component even if it already exists")

    def handle(self, **kwargs):
        """Create a new component in the components directory."""

        # A live component is a class as well as a template, which make:live knows how to write
        if kwargs.get("live") or kwargs.get("inline"):
            make_live = importlib.import_module("pyblade.cli.commands.make:live").Command()
            return make_live.handle(
                name=kwargs.get("name"),
                app=kwargs.get("app"),
                inline=kwargs.get("inline"),
                force=kwargs.get("force"),
            )

        name = pascal_to_snake(kwargs.get("name"))
        path, component_name = split_dotted_path(name)

        if not path and component_name == "slot":
            self.error("You are not allowed to create a 'slot' component at the root level.")
            return

        try:
            base = target_directory("components", kwargs.get("app"))
        except LocationError as error:
            self.error(str(error))
            return

        components_dir = base / path
        components_dir.mkdir(parents=True, exist_ok=True)

        component_file = components_dir / f"{component_name}.html"

        if component_file.exists() and not kwargs.get("force"):
            self.error(f"Component '{component_name}' already exists at {shown(component_file)}")
            self.tip(
                "Use [bright_black]--force[/bright_black] to override the existing "
                "component or choose a different name."
            )
            return

        html_stub = config.paths.stubs / "templates/component.html.stub"
        if not html_stub.exists():
            self.error("Component stub not found.")
            return

        with open(html_stub, "r") as file:
            component_template = file.read()

        with open(component_file, "w") as f:
            f.write(component_template)

        self.success(f"Component created successfully at '{shown(component_file)}'")
