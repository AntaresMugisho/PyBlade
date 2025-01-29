from typing import Any, Dict, List

import click
import questionary
from rich.progress import track

from ..exceptions import PyBladeException
from ..utils.console import console
from ..utils.settings import settings


class BaseCommand:
    name: str = ""
    description: str = ""
    arguments: List[str] = []
    options: Dict[str, Dict[str, Any]] = {}
    aliases: List[str] = []

    def __init__(self):
        self.console = console
        self.validate_command_config()

        self.settings = settings

    def validate_command_config(self):
        if not self.name:
            raise PyBladeException("Command name must be defined")
        if not self.description:
            raise PyBladeException("Command description must be defined")

    def handle(self, **kwargs):
        raise NotImplementedError("Command must implement handle method")

    def argument(self, arg: str):
        """Must return the value of the argument if it exists or None if not"""
        pass

    def option(self, option_name: str):
        """Must return the value of the option if it exists or None if not"""
        pass

    # Prompting for inputs
    def ask(self, message: str, default: str = "") -> str:
        return questionary.text(message, default=default).ask()

    def confirm(self, message: str, default: bool = False) -> bool:
        return questionary.confirm(message, default=default).ask()

    def choice(self, message: str, choices: List[str], default: str | None = None) -> str:
        return questionary.select(message, choices, default=default).ask()

    def select(self, message: str, choices: List[str], default: str | None = None) -> str:
        return questionary.select(message, choices, default=default).ask()

    def checkbox(self, message: str, choices: List[str], default: List[str] | None = []) -> List[str]:
        return questionary.checkbox(message, choices, default=default).ask()

    def secret(self, message: str, default: str = "") -> str:
        return questionary.password(message, default=default).ask()

    # Command output
    def info(self, message: str):
        self.console.print(f"[blue]{message}[/blue]")

    def success(self, message: str):
        self.console.print(f"[green]✔️ {message}[/green]")

    def error(self, message: str):
        self.console.print(f"[red]❌ {message}[/red]")

    def warning(self, message: str):
        self.console.print(f"[yellow]⚠️ {message}[/yellow]")

    def line(self, message: str):
        self.console.print(message)

    def new_line(self, n: int = 1):
        self.console.print("\n" * n)

    def newline(self, n: int = 1):
        self.new_line(n)

    def track(self, items: List[Any], description: str = "Processing...\n"):
        return track(items, description=f"{description}\n")

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
