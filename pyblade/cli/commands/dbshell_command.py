from .django_command import DjangoCommand


class DbShellCommand(DjangoCommand):
    name = "db:shell"
    aliases = ["dbshell"]
    description = "Run a database shell"
    django_command = "dbshell"

    def handle(self, **kwargs):
        """Start a database shell."""
        self._run_django_command()
