import click
import questionary
from questionary import Choice, Style
from rich.console import Console
from rich.table import Table

import pkgutil
import importlib
from pathlib import Path
from commands.base_command import BaseCommand

# from pyblade.cli.command.add import liveblade
# from pyblade.cli.command.migrate import migrate

def load_commands():
    commands = []
    commands_path = Path(__file__).parent / "commands"

    # Load built-in commands
    for _, name, _ in pkgutil.iter_modules([str(commands_path)]):
        module = importlib.import_module(f"commands.{name}")
        for item_name in dir(module):
            item = getattr(module, item_name)
            if isinstance(item, type) and issubclass(item, BaseCommand) and item != BaseCommand:
                commands.append(item)

    # Load project commands if they exist
    project_commands_path = Path.cwd() / "pyblade_commands"
    if project_commands_path.exists():
        # Similar loading logic for project commands
        pass

    return commands

class CommandGroup(click.Group):
    def format_help(self, ctx, formatter):
        console = Console()

        # Project header
        console.print(
            "\n[bold blue]PyBlade CLI[/bold blue]\n[italic] Modern Template Engine for Python web frameworks [/italic]"
        )

        # Group commands by category
        categories = {
            "Project Commands": ["init", "serve", "migrate"],
            "Generator Commands": ["make:component", "make:layout"],
            "Database Commands": ["db:migrate", "db:rollback", "db:seed", "db:reset", "db:refresh"],
            "Utility Commands": ["cache:clear", "view:clear"],
        }

        for category, commands in categories.items():
            table = Table(show_header=True, header_style="bold magenta", box=None)
            table.add_column("Command", style="cyan")
            table.add_column("Description", style="white")

            console.print(f"\n[bold yellow]{category}[/bold yellow]")

            for cmd_name in commands:
                cmd = self.get_command(ctx, cmd_name)
                if cmd:
                    table.add_row(cmd_name, cmd.help or "")

            console.print(table)

        console.print("\nUse [cyan]pyblade COMMAND --help[/cyan] for more information about a command.\n")


@click.group(cls=CommandGroup)
def cli():
    """PyBlade - Modern Template Engine for Python web frameworks"""
    pass

    # framework = choose_framework()

    # ensure_django_installed()

    # print(f"[✔️ INFO] Creating a new Django project: {project_name}")
    # subprocess.check_call(['django-admin', 'startproject', project_name])

    # if questionary.confirm("Do you want to use liveBlade?").ask():
    #     configure_pyblade(project_name)

    # configure_framework(framework, project_name)

    # print("[🎉 SUCCESS] The Django project has been successfully initialized.")


# Register all commands
for command_class in load_commands():
    cli.add_command(command_class.create_click_command())


if __name__ == "__main__":
    cli()
