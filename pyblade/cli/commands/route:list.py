from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Show all registered routes information.
    """

    name = "route:list"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade route:list' command"""
        ...
