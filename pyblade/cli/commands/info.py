from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Show information about the current project and environment.
    """

    name = "info"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade info' command"""
        ...
