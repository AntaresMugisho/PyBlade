import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

TEMPLATES_DIR = BASE_DIR.joinpath("templates")

CURRENT_PATH = ""


def load_template(template_name: str, template_dirs: list | None = None) -> str:
    """
    Loads the template file.

    :param template_dirs: The list of directories where to find templates
    :param template_name: The template name.
    :return: The template content as string.
    """
    # Optionally remove .html extension if added
    template_name = template_name.rstrip(".html").replace(".", "/")

    for directory in template_dirs:
        template_path = f"{directory.joinpath(template_name)}.html"

        if os.path.exists(template_path):
            with open(template_path, "r") as file:
                return file.read()

    raise Exception("PyBlade Template Not Found")
