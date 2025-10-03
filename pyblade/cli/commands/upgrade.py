from pyblade.cli import BaseCommand
from pyblade.utils import get_version, run_command


class Command(BaseCommand):
    """
    Upgrade PyBlade to the latest available version.
    """

    name = "upgrade"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""
        ...

    def handle(self, **kwargs):
        """Execute the 'pyblade upgrade' command"""

        version_before = get_version()
        try:
            run_command("pip install --upgrade pyblade")
        except Exception as e:
            self.error(f"Failed to upgrade PyBlade: {e}")
            return

        version_after = get_version()
        if version_before == version_after:
            self.info(f"Looks like you have the latest PyBlade version ({version_before}) !")
        else:
            self.success(f"PyBlade has been upgraded to the latest version ({version_after}).")
