from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Login to your PyBlade account.
    """

    name = "login"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade login' command"""
        ...
