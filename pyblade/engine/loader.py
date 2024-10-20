from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

TEMPLATES_DIR = BASE_DIR.joinpath("templates")

CURRENT_PATH = ""


def load_template(template_name: str) -> str:
    """
    Loads the template file.

    :param template_name: The template name.
    :return: The template content as string.
    """

    folders = [a for a in template_name.split(".")]
    file_path = TEMPLATES_DIR
    for folder in folders:
        file_path = file_path.joinpath(folder)

    try:
        with open(f"{file_path}.html", "r") as file:
            return file.read()
    except FileNotFoundError as e:
        raise e
