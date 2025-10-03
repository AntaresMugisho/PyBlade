from pyblade.cli import BaseCommand
from pyblade.utils import run_django_command


class Command(BaseCommand):
    """
    Start a lightweight web server for development.
    """

    name = "serve"
    django_name = "runserver"
    # aliases = "runserver"

    _default_host = "127.0.0.1"
    _default_port = 8000

    def config(self):
        self.add_argument("addrport", required=False, default=f"{self._default_host}:{self._default_port}")

        self.add_option("-h", "--host", help="The host to bind to", default=f"{self._default_host}")
        self.add_option("-p", "--port", help="The port to bind to", default=f"{self._default_port}")
        self.add_flag("--no-reload", "--noreload", help="Disable auto-reload")
        self.add_flag("--ipv6", "-6", help="Tells Django to use an IPv6 address")
        self.add_flag("--insecure", help="Allows serving static files even if DEBUG is False")
        self.add_flag("--nostatic", help="Tells Django not to automatically serve static files at STATIC_URL")
        self.add_flag("--skip-checks", help="Skip system checks")
        self.add_option(
            "--settings",
            help=(
                'The Python path to a settings module, e.g. "myproject.settings.main". '
                "If this isn't provided, the DJANGO_SETTINGS_MODULE environment variable will be used."
            ),
        )
        self.add_option(
            "--pythonpath",
            help="A directory to add to the Python path, e.g. '/home/djangoprojects/myproject'.",
        )
        self.add_flag("--no-color", "--nocolor", help="Don't colorize the command output")
        self.add_flag("--force-color", help="Force colorization of the command output")
        self.add_flag("--version", help="Show program's version number and exit")
        self.add_option(
            "--verbosity",
            help="Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output",
            default=1,
        )
        self.add_flag("--traceback", help="Raise on CommandError exceptions")
        self.add_flag("--skip-checks", help="Skip system checks")

    def handle(self, **kwargs):
        try:
            host = kwargs.get("host") or self._default_host
            port = kwargs.get("port") or self._default_port
            addrport = kwargs.get("addrport") or f"{host}:{port}"
            noreload = kwargs.get("no_reload")

            command = [self.django_name, addrport]
            if noreload:
                command.append("--noreload")

            print(command)
            # self.line(f"Starting development server at http://{addrport}/\n")
            run_django_command(command)
        except Exception as e:
            self.error(f"Error: {e}")
