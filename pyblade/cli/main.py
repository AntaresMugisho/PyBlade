import importlib
import pkgutil
from pathlib import Path

import click
from rich.table import Table

from pyblade.cli import BaseCommand

from .utils.console import console
from .utils.version import __version__

_CACHED_COMMANDS = {}

DEFAULT_COMMANDS = {
    "Project commands": ["init", "convert", "serve", "deploy"],
    "PyBlade commands": [
        "cache:clear",
        "config:cache",
        "docs",
        "info",
        "login",
        "logout",
        "make:command",
        "make:component",
        "make:liveblade",
        "make:template",
        "route:list",
        "stubs",
        "update",
        "upgrade",
    ],
    # "Django commands": [
    #     "db:migrate",
    #     "db:shell",
    #     "shell",
    #     "app:start",
    #     "static:collect",
    #     "make:migrations",
    #     "make:messages",
    #     "compile:messages",
    # ],
}


def get_commands():

    # Load PyBlade Commands
    for category, commands in DEFAULT_COMMANDS.items():
        for cmd_name in commands:
            cmd = load_command("pyblade.cli.commands", cmd_name)
            click_cmd = register(cmd)

            # Add it to the appropriate category
            _CACHED_COMMANDS.setdefault(category, []).append(click_cmd)

    # # Load custom commands
    # for cmd_name in find_commands("management/commands"):
    #     cmd = load_command("management.commands", cmd_name)
    #     click_cmd = register(cmd)

    #     # Add it to the 'Custom commands' category
    #     _CACHED_COMMANDS.setdefault("Custom Commands", []).append(click_cmd)


def load_command(module_dir, cmd_name):
    module = importlib.import_module(f"{module_dir}.{cmd_name}")
    cmd = module.Command()
    if isinstance(cmd, BaseCommand):
        return cmd
    raise Exception("PyBlade Command must inherit 'pyblade.cli.BaseCommand'")


def find_commands(command_dir=None):
    command_dir = Path(command_dir)
    return [name for _, name, is_pkg in pkgutil.iter_modules([command_dir]) if not is_pkg and not name.startswith("_")]


def register(cmd):
    click_cmd = cmd.create_click_command()
    cli.add_command(click_cmd)
    for alias in cmd.aliases:
        cli.add_command(click_cmd, name=alias)
    return click_cmd


class CommandGroup(click.Group):

    def format_help(self, ctx, formatter):
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


@click.group(cls=CommandGroup)
@click.version_option("", "-v", "--version", message=f"\npyblade {__version__}\n")
@click.help_option("-h", "--help")
def cli():
    """PyBlade CLI - The modern Python web frameworks development toolkit"""


get_commands()

if __name__ == "__main__":
    cli()
