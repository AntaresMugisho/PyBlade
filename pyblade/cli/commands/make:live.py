from pyblade.cli import BaseCommand
from pyblade.cli.locations import LocationError, shown, target_directory
from pyblade.config import config
from pyblade.utils import pascal_to_snake, snakebab_to_pascal, split_dotted_path


class Command(BaseCommand):
    """
    Create a new Live component.
    """

    name = "make:live"
    aliases = ["make:livecomponent"]

    def config(self):
        """Setup command arguments and options here"""
        self.add_argument("name")
        self.add_option("-a", "--app", help="Create it in the components of this Django app, instead of the project's")
        self.add_flag(
            "-i",
            "--inline",
            help="Embed the HTML template in the Python component class file",
        )
        self.add_flag("-f", "--force", help="Create the Live component even if it already exists")

    def handle(self, **kwargs):
        """Create a new Live component."""

        name = pascal_to_snake(kwargs.get("name"))
        path, component_name = split_dotted_path(name)

        # A component of any size grows a stylesheet, a test, a partial. Keeping
        # its class and its template together in a folder of its own leaves
        # somewhere for those to go; a project that would rather have them side
        # by side in the components directory says so.
        folder = component_name if config.live_components.own_folder else ""

        try:
            base = target_directory("components", kwargs.get("app"))
        except LocationError as error:
            self.error(str(error))
            return

        component_dir = base / path / folder
        component_dir.mkdir(parents=True, exist_ok=True)

        html_file = component_dir / f"{component_name}.html"
        python_file = component_dir / f"{component_name}.py"

        # Check for existing files
        if html_file.exists() or python_file.exists():
            if not kwargs.get("force"):
                self.error(f"Component '{component_name}' already exists at {shown(python_file)}")
                self.tip(
                    "Use [bright_black]--force[/bright_black] to override the existing "
                    "component or choose a different name."
                )
                return

        stubs_dir = config.paths.stubs / "live"

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
                class_name=snakebab_to_pascal(component_name), template_name=shown(html_file)
            )

        with open(python_file, "w") as file:
            file.write(python_template)

        self.success("Live component created successfully:")
        if not kwargs.get("inline"):
            self.line(f"  - HTML: {shown(html_file)}")
        self.line(f"  - Python: {shown(python_file)}")
