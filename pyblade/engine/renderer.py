from pathlib import Path

from django.http import HttpResponse

from .loader import load_template
from .parser import Parser


class PyBlade:

    def __init__(self, dirs=None, app_dirs=None):
        self._dirs = dirs
        self._app_dirs = app_dirs
        self.parser = Parser()

    def render(self, template: str, context: dict) -> str:
        """
        Render the parsed template content with replaced values.

        :param template: The file name without extension
        :param context:
        :return:
        """
        template = load_template(template, self._dirs)
        template = self.parser.parse(template, context)

        return template

    def from_string(self):
        return "FROM STRING"


def render(request, template_name, context=None):
    if context is None:
        context = {}
    engine = PyBlade(
        [
            Path("/home/antares/Documents/Coding/Python/PyBlade/examples/django_backend/example/app/templates"),
            Path("/home/antares/Documents/Coding/Python/PyBlade/examples/django_backend/example/example/templates"),
        ],
        True,
    )
    return HttpResponse(engine.render(template_name, context))
