from typing import List, Optional

from ..utils import command
from .base_command import BaseCommand


class DjangoCommand(BaseCommand):
    """Base class for Django-specific commands."""

    django_command: str = ""  # The Django management command to run

    def __init__(self):
        super().__init__()

    def _check_django_project(self):
        """Check if we're in a Django project directory."""
        manage_py = self.settings.pyblade_root / "manage.py"
        if not manage_py.exists():
            raise FileNotFoundError(
                "manage.py not found. "
                "Please make sure you're in a Django project directory and you are in the environment."
            )

    def _run_django_command(self, args: Optional[List[str]] = None, capture_output: bool = False) -> Optional[str]:
        """Run a Django management command."""
        if not self.django_command:
            raise ValueError("django_command must be set in the command class")

        self._check_django_project()

        cmd = ["python", "manage.py", self.django_command]
        if args:
            cmd.extend(args)

        try:
            output = command.run(cmd, cwd=self.settings.pyblade_root)
            return output
        except command.RunError as e:
            self.error(e.stderr)
            return
