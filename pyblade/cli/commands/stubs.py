from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Generate PyBlade stub files for customization.
    """

    name = "stubs"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade stubs' command"""
        ...
