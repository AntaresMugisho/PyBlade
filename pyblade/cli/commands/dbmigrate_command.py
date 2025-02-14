from typing import List

from .django_command import DjangoCommand


# TODO: Fix this command
class DbMigrateCommand(DjangoCommand):
    name = "db:migrate"
    description = "Run database migrations"
    django_command = "migrate"
    arguments = ["app", "migration"]
    options = {
        "app": {
            "help": "Run migrations for a specific app.",
            "required": False,
        },
        "migration": {
            "help": "Run migrations for a specific migration.",
            "required": False,
        },
    }

    def handle(self, **kwargs):
        """Run database migrations."""
        app_name = kwargs.get("app")
        migration = kwargs.get("migration")

        args: List[str] = []
        if app_name:
            args.append(app_name)
            if migration:
                args.append(migration)

        self._run_django_command(args)
