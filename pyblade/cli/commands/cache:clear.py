from pyblade.cli import BaseCommand
from pyblade.engine.parsing.cache import TemplateCache


class Command(BaseCommand):
    """
    Clear templates cache
    """

    name = "cache:clear"

    def handle(self):
        TemplateCache().clear()
        self.success("Templates cache cleared successfully.")
