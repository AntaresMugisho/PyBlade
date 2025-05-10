from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Cache the configuration files to speed up application boot time
    """

    name = "config:cache"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade config:cache' command"""
        ...
