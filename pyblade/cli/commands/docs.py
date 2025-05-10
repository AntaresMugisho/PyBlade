from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Open the PyBlade CLI documentation in your default browser.
    """

    name = "docs"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade docs' command"""
        ...
