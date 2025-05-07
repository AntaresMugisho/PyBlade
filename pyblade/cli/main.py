# import functools
import importlib

# import os
import pkgutil
from pathlib import Path

import click
from rich.table import Table

from .utils.console import console
from .utils.version import __version__

DEFAULT_COMMANDS = {
    "Project commands": ["init", "serve"],
    "PyBlade commands": [
        "make:command",
        "hello",
        # "make:component",
        # "make:liveblade",
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

_CACHED_COMMANDS = {}


def load_commands():
    for category, commands in DEFAULT_COMMANDS.items():
        commands = sorted(commands)
        for cmd_name in commands:
            if cmd_name in _CACHED_COMMANDS.get(category, []):
                continue

            module = importlib.import_module(f"pyblade.cli.commands.{cmd_name}")

            cmd_cls = getattr(module, "Command")
            cmd_instance = cmd_cls.create_click_command()
            cli.add_command(cmd_instance)

            # Register aliases
            for alias in cmd_cls.aliases:
                cli.add_command(cmd_instance, name=alias)

            _CACHED_COMMANDS.setdefault(category, []).append(cmd_instance)


class CommandGroup(click.Group):
    def format_help(self, ctx, formatter):

        console.print(
            """
[bold]Welcome in the [blue]PyBlade CLI[/blue][/bold]
[italic]- The modern Python web frameworks development toolkit -[/italic]

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


def find_commands(command_dir=None):
    """
    Given a path to a command directory, return a list of all the command
    names that are available.
    """

    command_dir = Path(command_dir) / "commands"
    return [name for _, name, is_pkg in pkgutil.iter_modules([command_dir]) if not is_pkg and not name.startswith("_")]


load_commands()

if __name__ == "__main__":
    cli()
