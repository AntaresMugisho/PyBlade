from pathlib import Path

from pyblade.cli import BaseCommand


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
        description = kwargs.get("description") or "Help message for this command goes here"
        # commands_dir = self.settings.pyblade_root / "management" / "commands"
        commands_dir = Path("/home/antares/coding/pyblade/pyblade/cli/commands")
        commands_dir.mkdir(parents=True, exist_ok=True)

        cmd_path = commands_dir / f"{name}.py"

        if not (kwargs.get("force")):
            if cmd_path.exists():
                self.error(f"A command with the name '{name}' already exists.")
                return

        with open(cmd_path, "w") as file:
            file.write(
                f'''from pyblade.cli import BaseCommand

class Command(BaseCommand):
    """
    {description}
    """

    name = "{name}"
    aliases = [] # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade {name}' command"""
        ...
'''
            )
