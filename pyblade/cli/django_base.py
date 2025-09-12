import os

import click

from pyblade.cli import BaseCommand
from pyblade.cli.utils import run_command
from pyblade.config import settings

# Mapping of Django commands to PyBlade command aliases
DJANGO_COMMAND_ALIASES = {
    "check": [],
    "compilemessages": ["messages:compile"],
    "createcachetable": [],
    "dbshell": ["db:shell"],
    "diffsettings": [],
    "dumpdata": ["data:dump"],
    "flush": [],
    "inspectdb": ["db:inspect"],
    "loaddata": ["data:load"],
    "makemessages": ["make:messages", "messages:make"],
    "makemigrations": ["make:migrations"],
    "migrate": [],
    "optimizemigration": ["migrations:optimize"],
    "runserver": ["serve"],
    "sendtestemail": [],
    "shell": [],
    "showmigrations": ["migrations:show"],
    "sqlflush": ["sql:flush"],
    "sqlmigrate": ["sql:migrate"],
    "sqlsequencereset": ["sql:reset"],
    "squashmigrations": ["migrations:squash"],
    "startapp": ["app:start"],
    "startproject": ["project:start"],
    "test": [],
    "testserver": ["server:test"],
}


class DjangoCommand(BaseCommand):
    """Wrapper for Django commands to integrate with Click."""

    def __init__(self, django_command_name: str, app_name: str):
        self.django_command_name = django_command_name
        self.app_name = app_name
        self._django_command = None
        self.name = django_command_name
        self.aliases = []

        super().__init__()

        # Set aliases for this command (if any)
        for cmd_name, aliases in DJANGO_COMMAND_ALIASES.items():
            if cmd_name == self.django_command_name:
                self.aliases = aliases
                if self.aliases:
                    self.name = self.aliases[0]
                    self.aliases[0] = self.django_command_name

    def handle(self, **kwargs):
        """Execute the equivalent Django command"""

        arguments = [a.get("name") for a in self.arguments]

        argv = []
        for param, value in kwargs.items():
            if value:
                if param in arguments:
                    # Handle positional arguments
                    argv.append(f"{value}")
                else:
                    # Handle flags
                    option = param.replace("_", "-")
                    if isinstance(value, bool):
                        argv.append(f"--{option}")
                    else:
                        # Hanlle options
                        argv.append(f"--{option}={value}")

        cmd = ["python", "manage.py", self.django_command_name, *argv]
        try:
            run_command(cmd, cwd=settings.root_dir)
        except Exception:
            pass

    def load_django_command(self):
        """Load the actual Django command to extract help text and arguments."""
        from django.core.management import load_command_class

        if not self._django_command:
            self._django_command = load_command_class(self.app_name, self.django_command_name)
        return self._django_command

    def get_help_text(self) -> str:
        """Extract help text from Django command."""
        cmd = self.load_django_command()
        return cmd.help or None

    def create_parser(self):
        """Create a parser for the Django command to extract options."""
        # if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        # # TODO: Find a way to load the settings from the current project
        #     os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.django_backend.django_backend.settings")

        cmd = self.load_django_command()
        parser = cmd.create_parser("", self.django_command_name)

        # Remove the DJANGO8SETTINGS_MODULE from env to prevent conflicts
        os.environ.pop("DJANGO_SETTINGS_MODULE")

        return parser

    def _reordered_actions(self, actions):
        """Copied from django"""

        show_last = {
            "--version",
            "--verbosity",
            "--traceback",
            "--settings",
            "--pythonpath",
            "--no-color",
            "--force-color",
            "--skip-checks",
        }
        return sorted(actions, key=lambda a: set(a.option_strings) & show_last != set())

    def config(self):
        parser = self.create_parser()

        if parser:
            actions = self._reordered_actions(parser._actions)
            for action in actions:
                # Skip the help action as Click adds it automatically
                if action.dest == "help":
                    continue

                # Skip suppressed actions
                if action.default == "==SUPPRESS==" or action.help == "==SUPPRESS==":
                    continue

                # Handle positional arguments
                if not action.option_strings:
                    if action.dest == "args":
                        # This is a cath-all for remaining arguments
                        self.add_argument(action.metavar, required=action.required, default=action.default)

                    else:
                        # Regular positional argument
                        self.add_argument(
                            action.dest,
                            # help=action.help,
                            required=action.required,
                            default=action.default,
                        )
                else:
                    # Handle optional arguments / flags
                    param_kwargs = {
                        "help": action.help or "",
                        "required": action.required,
                    }

                    # Handle default values
                    if action.default:
                        param_kwargs["default"] = action.default

                    # Determine option type
                    if action.type:
                        # if action.type == int:
                        #     param_kwargs["type"] = click.INT
                        # elif action.type == float:
                        #     param_kwargs["type"] = click.FLOAT
                        if action.type == bool:
                            param_kwargs["is_flag"] = True
                            param_kwargs["default"] = None

                    # Handle choices if available (This is commented cause it's causing some types errors in click)
                    # if action.choices:
                    # param_kwargs["type"] = click.Choice(action.choices)

                    # Add the option in the list
                    self.add_option(*action.option_strings, **param_kwargs)

    def create_click_command(self) -> click.Command:
        """Create a Click command that mirrors Django command parameters."""
        self.config()
        help_text = self.get_help_text()

        @click.command(name=self.name, help=help_text)
        def click_command(**kwargs):
            return self.handle(**kwargs)

        for argument in self.arguments:
            click_command = click.argument(
                argument.get("name"), required=argument.get("required"), default=argument.get("default")
            )(click_command)

        for option in self.options:
            click_command = click.option(
                *option.get("name"),
                help=option.get("help"),
                required=option.get("required"),
                default=option.get("default"),
                is_flag=option.get("is_flag", False),
            )(click_command)

        return click_command
