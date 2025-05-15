import os
from typing import List, Optional

import click

from pyblade.cli import BaseCommand

from .utils import command

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


class DjangoCommandWrapper(BaseCommand):
    """Wrapper for Django commands to integrate with Click."""

    def __init__(self, django_command_name: str, app_name: str):
        self.django_command_name = django_command_name
        self.app_name = app_name
        self._django_command = None
        self.name = django_command_name
        self.aliases = []

        # Set aliases for this command (if any)
        for cmd_name, aliases in DJANGO_COMMAND_ALIASES.items():
            if cmd_name == self.django_command_name:
                self.aliases = aliases
                if self.aliases:
                    self.name = self.aliases[0]
                    self.aliases[0] = self.django_command_name

    def handle(self, **kwargs):
        self.info("Test")
        self.warning("Test")
        self.error("Test")
        self.success("Test")
        # self.error(f"This will run [python manage.py {kwargs}")

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
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.django_backend.django_backend.settings")

        cmd = self.load_django_command()
        parser = cmd.create_parser("manage.py", self.django_command_name)
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

    def create_click_command(self) -> click.Command:
        """Create a Click command that mirrors Django command parameters."""
        help_text = self.get_help_text()
        parser = self.create_parser()

        @click.command(name=self.name, help=help_text)
        def click_command(**kwargs):
            return self.handle(**kwargs)

        if parser:
            actions = self._reordered_actions(parser._actions)
            for action in actions:
                # Skip the help action as Click adds it automatically
                if action.dest == "help":
                    continue

                # Handle positional arguments
                if not action.option_strings:
                    if action.dest == "args":
                        # This is a cath-all for remaining arguments
                        # self.add_argument(action.metavar, required=action.required, help=action.help)
                        click_command = click.argument(
                            action.metavar,
                            # help=action.help,
                            required=action.required,
                        )(click_command)
                    else:
                        # Regular positional argument
                        click_command = click.argument(
                            action.dest,
                            # help=action.help,
                            required=action.required,
                        )(click_command)
                else:
                    # Handle optional arguments / flags
                    param_kwargs = {
                        "help": action.help or "",
                        "required": action.required,
                    }

                    # Determine option type
                    if action.type:
                        if action.type == int:
                            param_kwargs["type"] = click.INT
                        elif action.type == float:
                            param_kwargs["type"] = click.FLOAT
                        elif action.type == bool:
                            param_kwargs["is_flag"] = True

                    # Handle choices if available
                    # if action.choices:
                    # param_kwargs["type"] = click.Choice(action.choices)

                    # Handle default values
                    if action.default and action.default != "==SUPPRESS==":
                        param_kwargs["default"] = action.default

                    # Create the Click Option
                    click_command = click.option(*action.option_strings, **param_kwargs)(click_command)
        return click_command


class DjangoCommand(BaseCommand):
    """Base class for Django-specific commands."""

    django_command: str = ""  # The Django management command to run

    def __init__(self):
        super().__init__()

    def _check_django_project(self):
        """Check if we're in a Django project directory."""
        manage_py = self.settings.pyblade_root / "manage.py"
        if not manage_py.exists():
            raise FileNotFoundError(
                "manage.py not found. "
                "Please make sure you're in a Django project directory and you are in the environment."
            )

    def _run_django_command(self, args: Optional[List[str]] = None, capture_output: bool = False) -> Optional[str]:
        """Run a Django management command."""
        if not self.django_command:
            raise ValueError("django_command must be set in the command class")

        cmd = ["python", "manage.py", self.django_command]
        if args:
            cmd.extend(args)

        try:
            output = command.run(cmd, cwd=self.settings.pyblade_root)
            return output
        except command.RunError as e:
            self.error(e.stderr)
            return
