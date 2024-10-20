from pathlib import Path

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

        BASE_DIR = Path(__file__).parent.parent.parent
        TEMPLATES_DIR = BASE_DIR.joinpath("templates")

        folders = [a for a in template_name.split(".")]
        file_path = TEMPLATES_DIR
        for folder in folders:
            file_path = file_path.joinpath(folder)

        try:
            with open(f"{file_path}.html", "r") as file:
                return file.read()
        except FileNotFoundError as e:
            raise e
