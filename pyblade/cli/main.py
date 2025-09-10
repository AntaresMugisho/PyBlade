import importlib
import pkgutil
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from pyblade.cli import BaseCommand
from pyblade.utils import get_version

from .django_base import DjangoCommand

console = Console()

# Default commands organized by category
DEFAULT_COMMANDS = {
    "Project commands": [
        "init",
        "convert",
        "serve",
        # "deploy"
    ],
    "PyBlade commands": [
        # "cache:clear",
        # "config:cache",
        "docs",
        "info",
        # "login",
        # "logout",
        "make:command",
        "make:component",
        "make:liveblade",
        "make:template",
        "tailwind:configure",
        "route:list",
        "stubs",
        "upgrade",
    ],
}

# Cache for commands
_CACHED_COMMANDS = {}


def get_project_config():
    """
    Get project configuration from pyblade.json.
    Returns None if the file doesn't exist or is invalid.
    """

    return None


def find_project_root():
    """Find the project root directory by looking for pyblade.json."""
    current_dir = Path.cwd()
    while current_dir != current_dir.parent:
        if (current_dir / "pyblade.json").exists():
            return current_dir
        current_dir = current_dir.parent
    return None


def load_commands():
    """Load all commands and categorize them."""

    # Load PyBlade commands
    for category, commands in DEFAULT_COMMANDS.items():
        for cmd_name in commands:
            try:
                cmd = load_command("pyblade.cli.commands", cmd_name)
                click_cmd = register(cmd)
                _CACHED_COMMANDS.setdefault(category, []).append(click_cmd)
            except (ImportError, AttributeError) as e:
                console.print(f"[red]Failed to load PyBlade Command {cmd_name}: {str(e)}[/red]")

    # Load Django commands if the project is based on Django Framework
    commands = load_django_commands()
    if commands:
        _CACHED_COMMANDS["Django commands"] = commands

    # Load custom commands
    # load_custom_commands()


def load_django_commands():
    """Load and register all Django commands."""
    django_commands = []

    try:
        from django.core.management import get_commands as get_django_commands

        django_commands_dict = get_django_commands()

        # Process Django commands
        for cmd_name, app_name in django_commands_dict.items():
            try:
                # Create wrapper for the Django command
                wrapper = DjangoCommand(cmd_name, app_name)
                click_cmd = register(wrapper)

                # Add command to our list
                django_commands.append(click_cmd)

            except Exception as e:
                click.echo(f"Failed to load Django command {cmd_name}: {str(e)}", err=True)

        return sorted(django_commands, key=lambda c: c.name)

    except ImportError:
        click.echo("Django not found. Django commands will not be available.", err=True)
        return []


def load_custom_commands():
    """Load custom commands from the project."""
    try:
        # Look for custom commands in multiple possible locations
        possible_dirs = [Path("management/commands"), Path("commands"), Path("cli/commands")]

        for custom_commands_dir in possible_dirs:
            if custom_commands_dir.exists():
                for cmd_name in find_commands(custom_commands_dir):
                    try:
                        module_dir = str(custom_commands_dir).replace("/", ".")
                        cmd = load_command(module_dir, cmd_name)
                        click_cmd = register(cmd)
                        _CACHED_COMMANDS.setdefault("Custom Commands", []).append(click_cmd)
                    except Exception as e:
                        console.print(f"[red]Failed to load custom command {cmd_name}: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Error while loading custom commands: {str(e)}[/red]")


def load_command(module_dir, cmd_name):
    """Load a command from a module."""
    module = importlib.import_module(f"{module_dir}.{cmd_name}")
    cmd = module.Command()
    if isinstance(cmd, BaseCommand):
        return cmd
    raise TypeError(f"Command {cmd_name} must inherit from 'pyblade.cli.BaseCommand'")


def find_commands(command_dir):
    """Find command modules in a directory."""
    return [
        name for _, name, is_pkg in pkgutil.iter_modules([str(command_dir)]) if not is_pkg and not name.startswith("_")
    ]


def register(cmd):
    """Register a command with Click CLI."""
    click_cmd = cmd.create_click_command()

    cli.add_command(click_cmd, name=cmd.name)

    for alias in cmd.aliases:
        cli.add_command(click_cmd, name=alias)
    return click_cmd


class CommandGroup(click.Group):
    """Custom Click group that displays a formatted help message."""

    def format_help(self, ctx, formatter):
        """Format the help text with Rich formatting."""
        console.print(
            """
[bold]Welcome in the [blue]PyBlade CLI[/blue][/bold]
[italic]- The modern Python web development toolkit -[/italic]

[bold italic]Usage[/bold italic]: [blue]pyblade COMMAND [ARGUMENTS] [OPTIONS] [/blue]

[bold italic]Options[/bold italic]:
  [blue]-h, --help[/blue]\tShow this message and exit.

[bold italic]Available commands[/bold italic]:
"""
        )

        table = Table(show_header=True, header_style="white", box=None)
        table.add_column("Command", justify="left")
        table.add_column("Description", justify="left")
        for category, commands in _CACHED_COMMANDS.items():

            table.add_row(f"\n[yellow]{category}[/yellow]")
            for cmd in commands:
                table.add_row(f"  [blue]{cmd.name}[/blue]", cmd.help)

        console.print(table)

        console.print("\nUse [blue]pyblade COMMAND --help[/blue] for more information about a specific command.\n")


version = get_version()


@click.group(cls=CommandGroup)
@click.version_option(version, "-v", "--version", message=f"\npyblade {version}\n")
@click.help_option("-h", "--help")
def cli():
    """PyBlade CLI - The modern Python web frameworks development toolkit"""


# Load commands when this module is imported
load_commands()

if __name__ == "__main__":
    cli()
