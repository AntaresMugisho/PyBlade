from typing import Any, Dict, List

import click

from pyblade.cli.exceptions import PyBladeException
from pyblade.cli.utils.console import console


class BaseCommand:
    name: str = ""
    description: str = ""
    arguments: List[str] = []
    options: Dict[str, Dict[str, Any]] = {}
    aliases: List[str] = []

    def __init__(self):
        self.console = console
        self.validate_command_config()

    def validate_command_config(self):
        if not self.name:
            raise PyBladeException("Command name must be defined")
        if not self.description:
            raise PyBladeException("Command description must be defined")

    def handle(self, **kwargs):
        raise NotImplementedError("Command must implement handle method")

    def confirm(self, message: str, default: bool = False) -> bool:
        return click.confirm(message, default=default)

    def info(self, message: str):
        self.console.print(f"[blue]{message}[/blue]")

    def success(self, message: str):
        self.console.print(f"[green]✔️ {message}[/green]")

    def error(self, message: str):
        self.console.print(f"[red]❌ {message}[/red]")

    def warning(self, message: str):
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")

    @classmethod
    def create_click_command(cls):
        cmd_instance = cls()

        @click.command(name=cls.name, help=cls.description)
        def click_command(**kwargs):
            return cmd_instance.handle(**kwargs)

        for arg in cls.arguments:
            click_command = click.argument(arg)(click_command)

        for option_name, option_config in cls.options.items():
            click_command = click.option(f"--{option_name}", **option_config)(click_command)

        return click_command
