import webbrowser

from pyblade.cli import BaseCommand


class Command(BaseCommand):
    """
    Open the PyBlade documentation in your default browser.
    """

    name = "docs"

    def handle(self):
        url = "https://docs.pyblade.dev"
        self.info(f"Opening PyBlade documentation in your browser: {url}")
        webbrowser.open(url)
