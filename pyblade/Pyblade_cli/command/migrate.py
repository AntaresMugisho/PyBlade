import questionary
import os
import re
import shutil
import subprocess
from command.core.convert import convert_django_to_pyblade


def migrate():
    project_directory = questionary.text(
        "Enter the path to the project directory (leave empty for the current directory):"
    ).ask()

    project_root = project_directory or os.getcwd()

    if not os.path.exists(project_root):
        print("[❌ ERROR] The specified project directory does not exist.")
        return

    output_directory = questionary.text("Enter the path to the output directory:").ask()

    if not output_directory:
        print("[❌ ERROR] You must specify an output directory.")
        return

    try:
        subprocess.check_call(['pip', 'install', 'pyblade'], stdout=subprocess.DEVNULL)
        print("[✔️ INFO] PyBlade installed successfully.")
    except subprocess.CalledProcessError:
        print("[❌ ERROR] PyBlade installation failed.")
        return

    if os.path.exists(output_directory):
        confirm_overwrite = questionary.confirm(
            "The output directory already exists. Do you want to overwrite it?"
        ).ask()
        if not confirm_overwrite:
            print("[ℹ️ INFO] Operation canceled.")
            return
        shutil.rmtree(output_directory)

    shutil.copytree(project_root, output_directory)
    print(f"[✔️ INFO] Project copied to: {output_directory}")

    html_templates = []
    for root, _, files in os.walk(output_directory):
        html_templates.extend(
            os.path.join(root, file) for file in files if file.endswith(".html")
        )

    settings_path = os.path.join(
        output_directory, os.path.basename(project_root), "settings.py"
    )

    if not os.path.exists(settings_path):
        print("[❌ ERROR] Settings file not found. Conversion aborted.")
        return

    with open(settings_path, "r", encoding="utf-8") as file:
        settings = file.read()

    if "import os" not in settings:
        settings = "import os\n" + settings

    updated_settings = settings.replace(
        "'DIRS': [],",
        "'DIRS': [os.path.join(BASE_DIR, 'templates')],"
    ).replace(
        "'django.template.backends.django.DjangoTemplates',",
        "'pyblade.backends.DjangoPyBlade',"
    )

    with open(settings_path, "w", encoding="utf-8") as file:
        file.write(updated_settings)

    print("[✔️ INFO] Updated settings.py for PyBlade integration.")

    if not html_templates:
        print("[⚠️ WARNING] No .html files found in the project.")
        return

    print(f"[✔️ INFO] {len(html_templates)} .html files found for conversion.")
    for template_path in html_templates:
        with open(template_path, "r", encoding="utf-8") as file:
            file_content = file.read()

        pyblade_content = convert_django_to_pyblade(file_content)

        with open(template_path, "w", encoding="utf-8") as file:
            file.write(pyblade_content)

        print(f"[✔️ INFO] Converted: {template_path}")

    print("[🎉 SUCCESS] Migration completed successfully!")


if __name__ == "__main__":
    migrate()
