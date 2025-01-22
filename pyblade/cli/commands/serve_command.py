from .django_command import DjangoCommand


class ServeCommand(DjangoCommand):
    name = "serve"
    aliases = ["runserver"]
    description = "Run the development server"
    options = {
        "host": {
            "help": "The host to bind to.",
            "default": "127.0.0.1",
        },
        "port": {
            "help": "The port to bind to.",
            "default": 8000,
        },
        "no-reload": {
            "help": "Disable auto-reloader.",
            "is_flag": True,
            "default": False,
        },
    }

    django_command = "runserver"

    def handle(self, **kwargs):
        """Start the development server."""
        host = kwargs.get("host", "127.0.0.1")
        port = kwargs.get("port", 8000)
        reload = not kwargs.get("no-reload", False)

        # Construct the address
        addr = f"{host}:{port}"

        args = [addr]
        if not reload:
            args.append("--no-reload")

        self._run_django_command(args)
