from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Hello command example
    """

    name = "hello"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade hello' command"""

        self.line("Holla")
