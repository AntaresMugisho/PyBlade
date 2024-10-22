from .loader import load_template
from .parser import Parser


class PyBlade:

    def __init__(self):
        self.parser = Parser()

    def render(self, template: str, context: dict) -> str:
        """
        Render the parsed template content with replaced values.

        :param template:
        :param context:
        :return:
        """
        template = load_template(template)
        template = self.parser.parse(template, context)

        return template
