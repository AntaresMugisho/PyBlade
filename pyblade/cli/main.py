import importlib
import pkgutil
from pathlib import Path

import click
from rich.table import Table

from pyblade.cli.commands.base_command import BaseCommand
from pyblade.cli.commands.collectstatic_command import CollectstaticCommand
from pyblade.cli.commands.db_makemigrations_command import DbMakemigrationsCommand
from pyblade.cli.commands.db_migrate_command import DbMigrateCommand
from pyblade.cli.commands.db_shell_command import DbShellCommand
from pyblade.cli.commands.shell_command import ShellCommand
from pyblade.cli.commands.startapp_command import StartappCommand
from pyblade.cli.utils.console import console


def load_commands():
    commands = []
    commands_path = Path(__file__).parent / "commands"

    # Load built-in commands
    for _, name, _ in pkgutil.iter_modules([str(commands_path)]):
        if name != "base_command":  # Skip the base command
            try:
                module = importlib.import_module(f"pyblade.cli.commands.{name}")
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, type) and issubclass(item, BaseCommand) and item != BaseCommand:
                        commands.append(item)
            except ImportError as e:
                print(f"Warning: Failed to load command module {name}: {e}")

    # Load project commands if they exist
    project_commands_path = Path.cwd() / "pyblade_commands"
    if project_commands_path.exists() and project_commands_path.is_dir():
        # Add project commands directory to Python path
        import sys

        sys.path.append(str(project_commands_path.parent))

        for _, name, _ in pkgutil.iter_modules([str(project_commands_path)]):
            try:
                module = importlib.import_module(f"pyblade_commands.{name}")
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, type) and issubclass(item, BaseCommand) and item != BaseCommand:
                        commands.append(item)
            except ImportError as e:
                console.print(f"Warning: Failed to load project command {name}: {e}")

    return commands


class CommandGroup(click.Group):
    def format_help(self, ctx, formatter):

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


def register_commands(cli):
    """Register all available commands."""
    commands = [
        InitCommand,
        ServeCommand,
        MigrateCommand,
        DbMigrateCommand,
        DbMakemigrationsCommand,
        DbShellCommand,
        ShellCommand,
        StartappCommand,
        CollectstaticCommand,
    ]
    for command_class in commands:
        cli.add_command(command_class.create_click_command())

    # Load project commands if they exist
    project_commands_path = Path.cwd() / "pyblade_commands"
    if project_commands_path.exists() and project_commands_path.is_dir():
        # Add project commands directory to Python path
        import sys

        sys.path.append(str(project_commands_path.parent))

        for _, name, _ in pkgutil.iter_modules([str(project_commands_path)]):
            try:
                module = importlib.import_module(f"pyblade_commands.{name}")
                for item_name in dir(module):
                    item = getattr(module, item_name)
                    if isinstance(item, type) and issubclass(item, BaseCommand) and item != BaseCommand:
                        cli.add_command(item.create_click_command())
            except ImportError as e:
                console.print(f"Warning: Failed to load project command {name}: {e}")


if __name__ == "__main__":
    register_commands(cli)
    cli()
