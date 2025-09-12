from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Start a lightweight web server for development.
    """

    name = "serve"
    django_name = "runserver"
    aliases = "runserver"

    _default_host = "127.0.0.1"
    _default_port = 8000

    def config(self):
        self.add_argument("addrport", required=False, default=f"{self._default_host}:{self._default_port}")

        self.add_option("-h", "--host", help="The host to bind to", default=f"{self._default_host}")
        self.add_option("-p", "--port", help="The port to bind to", default=f"{self._default_port}")
        self.add_option("--no-reload", "--noreload", help="Disable auto-reload", is_flag=True)

    def handle(self, **kwargs):
        host = kwargs.pop("host")
        port = kwargs.pop("port")
        no_reload = kwargs.pop("no_reload")
        addrport = kwargs.pop("addrport")

        # Construct the address
        addr = addrport or f"{host}:{port}"
        kwargs.setdefault(addr)
        if no_reload:
            kwargs.setdefault("--noreload")
