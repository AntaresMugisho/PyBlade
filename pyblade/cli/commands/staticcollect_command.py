import click

from .django_command import DjangoCommand


class StaticCollectCommand(DjangoCommand):
    name = "static:collect"
    description = "Collect static files"
    django_command = "collectstatic"
    aliases = ["collectstatic"]
    arguments = []
    options = {
        "no_input": {
            "help": "Do NOT prompt the user for input of any kind.",
            "is_flag": True,
        },
        "clear": {
            "help": "Clear the existing files before collecting.",
            "is_flag": True,
        },
    }

    def handle(self, **kwargs):
        """Collect static files."""
        no_input = kwargs.get("no_input", False)
        clear = kwargs.get("clear", False)

        args = []
        if no_input:
            args.append("--noinput")
        if clear:
            args.append("--clear")

        try:
            self._run_django_command(args)
            self.success("Static files collected successfully.")
        except Exception as e:
            self.error(f"Failed to collect static files: {str(e)}")

    @classmethod
    def create_click_command(cls):
        cmd_instance = cls()

        @click.command(name=cls.name, help=cls.description)
        @click.option("--no-input", is_flag=True, help="Do NOT prompt the user for input of any kind.")
        @click.option("--clear", is_flag=True, help="Clear the existing files before collecting.")
        def click_command(no_input: bool, clear: bool):
            return cmd_instance.handle(no_input=no_input, clear=clear)

        return click_command
