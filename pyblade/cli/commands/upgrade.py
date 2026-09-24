from pyblade.cli import BaseCommand, packages
from pyblade.config import config
from pyblade.utils import get_version


class Command(BaseCommand):
    """
    Upgrade PyBlade to the latest available version.
    """

    name = "upgrade"
    aliases = []  # Other possible names for the command

    def config(self):
        """Setup command arguments and options here"""

    def handle(self, **kwargs):
        """Execute the 'pyblade upgrade' command"""

        manager = packages.python_manager(config.root)
        command = packages.python_upgrade_command(manager, ["pyblade"])

        if command is None:
            self.error(
                "PyBlade has no environment it may upgrade itself in.\n"
                " Activate the virtualenv this project uses, or upgrade it with whatever installed it."
            )
            return

        version_before = get_version()

        with self.status(f"Upgrading PyBlade with {manager}..."):
            result = packages.install(command, cwd=config.root)

        if result.returncode != 0:
            self.error(f"`{packages.as_typed(command)}` failed:\n{result.stderr.strip()}")
            return

        version_after = get_version()
        if version_before == version_after:
            self.info(f"Looks like you have the latest PyBlade version ({version_before}) !")
        else:
            self.success(f"PyBlade has been upgraded to the latest version ({version_after}).")
