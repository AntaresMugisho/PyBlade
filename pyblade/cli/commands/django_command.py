import subprocess
from pathlib import Path
from typing import List, Optional

from .base_command import BaseCommand


class DjangoCommand(BaseCommand):
    """Base class for Django-specific commands."""

    django_command: str = ""  # The Django management command to run

    def __init__(self):
        super().__init__()
        self._check_django_project()

    def _check_django_project(self):
        """Check if we're in a Django project directory."""
        manage_py = Path("manage.py")
        if not manage_py.exists():
            raise FileNotFoundError(
                "manage.py not found. Please run this command from your Django project root directory."
            )

    def _run_django_command(self, args: Optional[List[str]] = None, capture_output: bool = False) -> Optional[str]:
        """Run a Django management command."""
        if not self.django_command:
            raise ValueError("django_command must be set in the command class")

        cmd = ["python", "manage.py", self.django_command]
        if args:
            cmd.extend(args)

        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            else:
                subprocess.run(cmd, check=True)
                return None
        except subprocess.CalledProcessError as e:
            self.error(f"Command failed: {e.stderr if e.stderr else str(e)}")
            raise
