import importlib

import click
from rich.table import Table

from .utils.console import console

DEFAULT_COMMANDS = {
    "Project Commands": [
        {
            "name": "init",
            "class": "InitCommand",
        },
        {
            "name": "migrate",
            "class": "MigrateCommand",
        },
        {
            "name": "serve",
            "class": "ServeCommand",
        },
    ],
    "Django Commands": [
        {
            "name": "db:migrate",
            "class": "DbMigrateCommand",
        },
        {
            "name": "shell",
            "class": "ShellCommand",
        },
    ],
}

_CACHED_COMMANDS = {}


def load_commands():
    for category, commands in DEFAULT_COMMANDS.items():
        for cmd in commands:
            cmd_name = cmd["name"]
            if cmd_name in _CACHED_COMMANDS.get(category, []):
                continue
            module = importlib.import_module(f"pyblade.cli.commands.{cmd_name.lower().replace(":", "")}_command")
            cmd_cls = getattr(module, cmd["class"])
            cmd_instance = cmd_cls.create_click_command()
            cli.add_command(cmd_instance)

            _CACHED_COMMANDS.setdefault(category, []).append(cmd_instance)


class CommandGroup(click.Group):
    def format_help(self, ctx, formatter):

        console.print(
            """
[bold]Welcome in the [blue]PyBlade CLI[/blue][/bold]

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
def cli():
    """PyBlade - Modern Template Engine for Python web frameworks"""
    pass


load_commands()

if __name__ == "__main__":
    cli()
