from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Deploy PyBlade application to PyBlade Cloud.
    """

    name = "deploy"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade deploy' command"""
        ...
