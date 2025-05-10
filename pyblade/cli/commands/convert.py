from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Convert existing Django or Jinja2 Templates to PyBlade Templates.
    """

    name = "convert"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade convert' command"""
        ...
