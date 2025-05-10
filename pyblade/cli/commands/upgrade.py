from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Upgrade PyBlade to the latest available version.
    """

    name = "upgrade"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade upgrade' command"""
        ...
