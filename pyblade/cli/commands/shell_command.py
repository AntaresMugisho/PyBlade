import click

from .django_command import DjangoCommand


class ShellCommand(DjangoCommand):
    name = "shell"
    description = "Run a Python shell with Django context"
    options = {
        "ipython": {
            "help": "Use IPython shell if available.",
            "is_flag": True,
        },
        "i": {
            "help": "Use IPython shell if available.",
            "is_flag": True,
        },
    }
    django_command = "shell"

    def handle(self, **kwargs):
        """Start a Python shell with Django context."""
        ipython = kwargs.get("ipython", False)

        args = []
        if ipython:
            args.append("-i")

        try:
            self._run_django_command(args)
        except Exception as e:
            self.error(f"Failed to start shell: {str(e)}")

    @classmethod
    def create_click_command(cls):
        cmd_instance = cls()

        @click.command(name=cls.name, help=cls.description)
        @click.option("--ipython", "-i", is_flag=True, help="Use IPython shell if available.")
        def click_command(ipython: bool):
            return cmd_instance.handle(ipython=ipython)

        return click_command
