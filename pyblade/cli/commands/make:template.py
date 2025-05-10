from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Create a new PyBlade template file.
    """

    name = "make:template"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade make:template' command"""
        ...
