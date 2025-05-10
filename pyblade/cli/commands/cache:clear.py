from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Clear all cached data from the application.
    """

    name = "cache:clear"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade cache:clear' command"""
        ...
