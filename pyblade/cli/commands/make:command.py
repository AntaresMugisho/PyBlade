from pyblade.cli import BaseCommand
from pyblade.config import settings
from pyblade.utils import get_project_root


class Command(BaseCommand):
    """
    Create a new PyBlade command file.
    """

    name = "make:command"

    def config(self):
        self.add_argument("name")
        self.add_option("-d", "--description", help="The description of the command")
        self.add_flag("-f", "--force", help="Create the command even if it already exists")

    def handle(self, **kwargs):
        name = kwargs.get("name")
        description = kwargs.get("description") or "Help message for this command should go here"
        commands_dir = get_project_root() / "management/commands"
        commands_dir.mkdir(parents=True, exist_ok=True)

        cmd_path = commands_dir / f"{name}.py"

        if not (kwargs.get("force")):
            if cmd_path.exists():
                self.error(f"A command with the name '{name}' already exists.")
                self.tip(
                    "Use [bright_black]--force[/bright_black] to override the existing "
                    "command or choose a different name."
                )
                return

        stubs_dir = settings.stubs_dir / "commands"
        cmd_template = stubs_dir / "command.py.stub"

        if not cmd_template.exists():
            self.error("Command stub not found.")
            return

        with open(cmd_template, "r") as file:
            cmd_template = file.read()

        with open(cmd_path, "w") as file:
            file.write(
                cmd_template.format(
                    name=name,
                    description=description,
                )
            )

        self.success(f"Command created successfully at '{cmd_path}'")
