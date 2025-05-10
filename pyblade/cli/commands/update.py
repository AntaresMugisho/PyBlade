from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Update PyBlade to the latest available version.
    """

    name = "update"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade update' command"""
        ...
