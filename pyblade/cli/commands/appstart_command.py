from .django_command import DjangoCommand


class AppStartCommand(DjangoCommand):
    name = "app:start"
    description = "Create a new Django app"
    aliases = ["startapp"]
    arguments = ["name"]
    options = {
        "directory": {
            "help": "Optional destination directory",
            "required": False,
        },
    }
    django_command = "startapp"

    def handle(self, **kwargs):
        """Create a new Django app."""
        app_name = kwargs.get("name")
        directory = kwargs.get("directory")

        args = [app_name]
        if directory:
            args.extend(["--directory", directory])

        try:
            self._run_django_command(args)
            self.success(f"App '{app_name}' created successfully.")
        except Exception as e:
            self.error(f"Failed to create app: {str(e)}")
