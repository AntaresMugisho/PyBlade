from collections import namedtuple
from typing import Any, Dict, List

import click
import questionary
from questionary import Style
from rich.console import Console
from rich.progress import track
from rich.theme import Theme

# Rich console config
console = Console(
    theme=Theme(
        {
            "info": "white on blue bold",
            "warning": "black on yellow bold",
            "danger": "white on red bold",
            "tip": "white on grey46 bold",
        }
    )
)

# Questionnary styles
questionnary_style = Style(
    [
        ("qmark", "fg:#673ab7 bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:blue"),  # submitted answer text behind the question
        ("pointer", "fg:yellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:blue bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:blue"),  # style for a selected item of a checkbox
        ("separator", "fg:#cc5454"),  # separator in lists
        ("instruction", "fg:gray italic"),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:#858585 italic"),  # disabled choices for select and checkbox prompts
        ("placeholder", "fg:#858585 italic"),
    ]
)


class Argument(click.Argument):
    """Custom argument class"""

    ...


class Option(click.Option):
    """Custom Option class"""

    ...


class ClickCommand(click.Command):
    """Custom Click Command class"""

    ...


class BaseCommand:
    name: str = ""
    help: str = ""  # Will come from the Command class docstring
    aliases: List[str] = []

    def __init__(self):
        self.arguments: List[Dict] = []
        self.options: List[Dict] = []

        if not self.name:
            raise Exception("Command must profide a 'name' attribute")

    # Command configuration
    def config(self):
        """Used to define command arguments and options"""
        pass

    def add_argument(self, name: str, required: bool = True, default: str | int | bool = None):
        self.arguments.append({"name": name, "required": required, "default": default})

    def add_option(
        self, *args, help: str, required: bool = False, is_flag: bool = False, default: str | int | bool = None
    ):
        self.options.append({"name": args, "help": help, "required": required, "default": default, "is_flag": is_flag})

    def add_flag(self, *args, help: str, required: bool = False):
        self.add_option(*args, help=help, required=required, is_flag=True)

    @classmethod
    def create_click_command(cls):
        cmd = cls()
        cmd.config()
        cmd.help = cls.help or (cls.__doc__.strip() if cls.__doc__ else "")

        # Create a click command function
        @click.command(name=cmd.name, help=cmd.help)
        def click_command(**kwargs):
            return cmd.handle(**kwargs)

        for params in cmd.arguments:
            name = params.pop("name")
            click_command = click.argument(name, **params)(click_command)

        for params in cmd.options:
            name = params.pop("name")
            # The name of a command option may be a tuple of strings (eg. ('-h', '--help'))
            click_command = click.option(*name, **params)(click_command)

        return click_command

    # Main command function handler
    def handle(self, **kwargs):
        """Used to define the command bihavior"""
        raise NotImplementedError("PyBlade Command must implement a 'handle' method")

    # Helpers
    def argument(self, arg: str):
        """Must return the value of the argument if it exists or None if not"""
        pass

    def option(self, option_name: str):
        """Must return the value of the option if it exists or None if not"""
        pass

    # Prompting for inputs
    def ask(self, message: str, default: str = "") -> str:
        return questionary.text(message, default=default, style=questionnary_style).unsafe_ask()

    def confirm(self, message: str, default: bool = False) -> bool:
        return questionary.confirm(message, default=default).unsafe_ask()

    def choice(self, message: str, choices: List, default: str | None = None) -> str:
        return questionary.select(message, choices, default=default).unsafe_ask()

    def checkbox(self, message: str, choices: List[str], default: List[str] | None = None) -> List[str]:
        return questionary.checkbox(message, choices, default=default).unsafe_ask()

    def secret(self, message: str, default: str | None = None) -> str:
        return questionary.password(message, default=default).unsafe_ask()

    def form(self, **questions):
        Response = namedtuple("Response", questions.keys())
        return Response(*[answer for answer in questions.values()])

    # Command output
    def info(self, message: str):
        console.print(f"\n [info] INFO [/info] {message}\n")

    def success(self, message: str):
        console.print(f"\n[green] ✔️[/green] [bold] {message}[bold]\n")

    def error(self, message: str):
        console.print(f"\n [danger] ERROR [/danger] {message}\n")

    def warning(self, message: str):
        console.print(f"\n [warning] WARN [/warning] {message}\n")

    def tip(self, message: str):
        console.print(f" [tip] TIP [/tip] {message}\n")

    def line(self, message: str):
        console.print(message)

    def new_line(self, n: int = 1):
        console.print("\n" * n)

    def newline(self, n: int = 1):
        self.new_line(n)

    def status(self, message: str):
        return console.status(f"[blue]{message}[/blue]\n")

    def track(self, items: List[Any], description: str = "Processing..."):
        return track(items, description=f"{description}\n")
