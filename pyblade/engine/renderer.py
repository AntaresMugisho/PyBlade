from .parser import Parser


class PyBlade:

    def __init__(self):
        self.parser = Parser()

    def render(self, template: str, context: dict) -> str:
        """
        Render the parsed template content

        :param template:
        :param context:
        :return:
        """
        template = self._load_template(template)
        template = self.parser.parse(template, context)

        return template

    @staticmethod
    def _load_template(template_name: str) -> str:
        """
        Loads the template file.

        :param template_name: The template name.
        :return: The template content as string.
        """

        try:
            with open(template_name, "r") as file:
                return file.read()
        except FileNotFoundError as e:
            raise e
