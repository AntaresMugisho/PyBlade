from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Help message for this command goes here
    """

    name = "example"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade example' command"""
        ...
