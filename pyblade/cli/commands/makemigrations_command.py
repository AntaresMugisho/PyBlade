from typing import List

from .django_command import DjangoCommand


# TODO: Fix this command
class MakeMigrationsCommand(DjangoCommand):
    name = "make:migrations"
    description = "Create new database migrations"
    aliases = ["makemigrations", "db:makemigrations"]
    options = {
        "empty": {
            "help": "Create an empty migration.",
            "is_flag": True,
        },
        "merge": {
            "help": "Enable fixing of migration conflicts.",
            "is_flag": True,
        },
    }

    django_command = "makemigrations"

    def handle(self, **kwargs):
        """Create new database migrations."""
        app_names = kwargs.get("app", [])
        print(app_names)
        empty = kwargs.get("empty", False)
        merge = kwargs.get("merge", False)

        args: List[str] = []
        if empty:
            args.append("--empty")
        if merge:
            args.append("--merge")
        args.extend(app_names)

        self._run_django_command(args, capture_output=False)
