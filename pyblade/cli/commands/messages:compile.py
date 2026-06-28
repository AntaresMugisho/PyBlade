from pyblade.cli import BaseCommand

class Command(BaseCommand):
    """
    Compiles .po files to .mo files for use with builtin gettext support.
    """

    name = "messages:compile"
    aliases = ["compile:messages"] # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade messages:compile' command"""
        ...
