import os

from .exceptions import TemplateNotFound
from .template import Template

TEMPLATE_EXTENSION = ".html"
TEMPLATE_DIRS = []

current_directory = None


def load_template(template_name: str, directories: list | None = None) -> Template:
    """
    Loads the template file.

    :param directories: List of template directories
    :param template_name: The template name.
    :return: The template content as string.
    """
    global TEMPLATE_DIRS

    if directories is not None:
        TEMPLATE_DIRS = directories

    template_name = template_name.replace(".", "/")

    for directory in TEMPLATE_DIRS:
        template_path = f"{directory.joinpath(template_name)}{TEMPLATE_EXTENSION}"

        if os.path.exists(template_path):
            with open(template_path, "r") as file:
                content = file.read()
                return Template(template_name, template_path, content)

    raise TemplateNotFound(f"{template_name}{TEMPLATE_EXTENSION}")
