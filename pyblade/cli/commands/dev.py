import os
import subprocess

from pyblade.cli import BaseCommand, packages, tailwind
from pyblade.cli.django_base import run_django_command
from pyblade.config import config


class Command(BaseCommand):
    """
    Start the development server, and build your stylesheet as you work.
    """

    name = "dev"
    django_name = "runserver"

    # What it used to be called, kept so that muscle memory still works
    aliases = ["serve"]

    _default_host = "localhost"
    _default_port = 8000

    def config(self):
        self.add_argument("addrport", required=False)

        self.add_option("-h", "--host", help="The host to bind to")
        self.add_option("-p", "--port", help="The port to bind to")
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
        self.add_option(
            "--verbosity",
            help="Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output",
            default=1,
        )
        self.add_flag("--no-reload", "--noreload", help="Disable auto-reload")
        self.add_flag("--ipv6", "-6", help="Tells Django to use an IPv6 address")
        self.add_flag("--insecure", help="Allows serving static files even if DEBUG is False")
        self.add_flag(
            "--nostatic",
            help="Tells Django to not automatically serve static files at STATIC_URL",
        )
        self.add_flag("--nothreading", help="Tells Django to not use threading")
        self.add_flag("--no-color", "--nocolor", help="Don't colorize the command output")
        self.add_flag("--force-color", help="Force colorization of the command output")
        self.add_flag("--traceback", help="Raise on CommandError exceptions")
        self.add_flag("--skip-checks", help="Skip system checks")
        self.add_flag("--no-css", help="Don't build the Tailwind stylesheet while the server runs")

    def handle(self, **kwargs):
        try:
            host = kwargs.get("host") or self._default_host
            port = kwargs.get("port") or self._default_port
            addrport = kwargs.get("addrport") or f"{host}:{port}"

            ipv6 = kwargs.get("ipv6")
            insecure = kwargs.get("insecure")
            noreload = kwargs.get("no_reload")
            nostatic = kwargs.get("nostatic")
            nothreading = kwargs.get("no_threading")
            traceback = kwargs.get("traceback")
            skip_checks = kwargs.get("skip_checks")
            force_color = kwargs.get("force_color")
            no_color = kwargs.get("no_color")

            command = [self.django_name, addrport]
            if noreload:
                command.append("--noreload")
            if ipv6:
                command.append("--ipv6")
            if insecure:
                command.append("--insecure")
            if nostatic:
                command.append("--nostatic")
            if nothreading:
                command.append("--nothreading")
            if traceback:
                command.append("--traceback")
            if skip_checks:
                command.append("--skip-checks")
            if force_color:
                command.append("--force-color")
            if no_color:
                command.append("--no-color")

            watcher = None if kwargs.get("no_css") else self._watch_stylesheet()

            try:
                run_django_command(command)
            finally:
                if watcher:
                    watcher.terminate()

        except Exception as e:
            self.error(str(e))

    def _watch_stylesheet(self):
        """Build the Tailwind stylesheet, and go on building it as templates change.

        Started only in the process the developer started, never in the one
        Django's reloader spawns: that one is replaced on every code change,
        and a watcher replaced with it would miss what happened in between.
        """
        if os.environ.get("RUN_MAIN") == "true":
            return None

        root = config.root

        if not tailwind.is_configured(root):
            return None

        manager = packages.js_manager(root)
        command = tailwind.build_command(manager, watch=True)

        if command is None:
            self.warning(
                "No JavaScript package manager was found, so your stylesheet will not be built.\n"
                " Run [blue]pyblade tailwind:config[/blue], or start the server with --no-css."
            )
            return None

        self.success(f"Watching your templates and building {tailwind.OUTPUT}.", bold=False)

        return subprocess.Popen(command, cwd=root)
