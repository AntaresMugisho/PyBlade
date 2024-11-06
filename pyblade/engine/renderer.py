from . import loader
from .exceptions import TemplateNotFound
from .parser import Parser


class PyBlade:

    def __init__(self, dirs=None):
        self._template_dirs = dirs or []
        self._parser = Parser()

    def render(self, template: str, context: dict | None = None) -> str:
        """
        Render the parsed template content with replaced values.

        :param template: The file string content
        :param context:
        :return:
        """
        if context is None:
            context = {}

        template_code = self._parser.parse(template, context)

        return template_code

    @staticmethod
    def from_string(template_code):
        return "FROM STRING"

    def get_template(self, template_name):
        try:
            template = loader.load_template(template_name, self._template_dirs)
            template.engine = self
        except TemplateNotFound as exc:
            raise exc

        return template
