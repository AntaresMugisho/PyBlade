from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Logout form your PyBlade account.
    """

    name = "logout"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade logout' command"""
        ...
