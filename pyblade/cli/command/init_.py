import os
import subprocess

import questionary

from pyblade.cli.command.core.edit_page import edit_html_file


def init():
    """Initializes a new Django project with PyBlade and a CSS framework."""

    project_name = questionary.text("Enter your project name:").ask()
    if not project_name:
        print("[❌ ERROR] The project name is required.")
        return

    framework = choose_framework()

    ensure_django_installed()

    print(f"[✔️ INFO] Creating a new Django project: {project_name}")

    if questionary.confirm("Do you want to use liveBlade?").ask():
        configure_pyblade(project_name)

    configure_framework(framework, project_name)

    print("[🎉 SUCCESS] The Django project has been successfully initialized.")


def configure_pyblade(project_name):
    """Configures PyBlade for the Django project."""
    subprocess.check_call(["pip", "install", "pyblade"])
    settings_path = os.path.join(project_name, project_name, "settings.py")

    try:
        with open(settings_path, "r") as file:
            settings = file.read()

        if "import os" not in settings:
            settings = "import os\n" + settings

        new_settings = settings.replace("'DIRS': [],", "'DIRS': [os.path.join(BASE_DIR, 'templates')],").replace(
            "'django.template.backends.django.DjangoTemplates',", "'pyblade.backends.DjangoPyBlade',"
        )

        with open(settings_path, "w") as file:
            file.write(new_settings)

        print("[✔️ INFO] The template engine has been replaced with PyBlade.")
    except FileNotFoundError:
        print(f"[❌ ERROR] 'settings.py' file not found in {settings_path}.")
        return

    try:
        with open("templates/default_urlconf.html", "r") as file:
            default_urlconf = file.read()

        for root, _, files in os.walk("."):
            if "default_urlconf.html" in files:
                edit_html_file(os.path.join(root, "default_urlconf.html"), default_urlconf)
    except FileNotFoundError:
        print("[❌ ERROR] 'default_urlconf.html' file not found.")


def configure_framework(framework, project_name):
    """Configures the chosen CSS framework."""
    if framework == "TailwindCSS":
        install_and_configure_tailwind(project_name)
    elif framework == "Bootstrap":
        install_and_configure_bootstrap(project_name)
    elif framework == "Other":
        framework_name = questionary.text("Enter the name of the CSS framework you want to install:").ask()
        if framework_name:
            subprocess.check_call(["npm", "install", framework_name])
            print(f"[✔️ INFO] {framework_name} has been installed. You need to configure it manually.")


def install_and_configure_bootstrap(project_name):
    """Installs and configures Bootstrap."""
    print("[✔️ INFO] Installing Bootstrap...")
    subprocess.check_call(["pip", "install", "django-bootstrap-v5"])

    static_dir = os.path.join(project_name, "static")
    os.makedirs(static_dir, exist_ok=True)

    css_file = os.path.join(static_dir, "styles.css")
    with open(css_file, "w") as file:
        file.write("@import 'bootstrap/dist/css/bootstrap.min.css';")

    print("[✔️ INFO] Bootstrap has been installed and configured. Add 'styles.css' to your templates.")


def install_and_configure_tailwind(project_name):
    """Installs and configures TailwindCSS with django-tailwind."""
    print("[✔️ INFO] Installing django-tailwind...")
    subprocess.check_call(["pip", "install", "django-tailwind"])

    settings_path = os.path.join(project_name, project_name, "settings.py")
    with open(settings_path, "r") as file:
        settings = file.read()

    new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'tailwind',  ").replace(
        "DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'",
        "DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField', \nTAILWIND_APP_NAME = 'theme' \n  ",
    )

    with open(settings_path, "w") as file:
        file.write(new_settings)
    print("[✔️ INFO] Creating the 'theme' app to manage Tailwind...")
    try:
        os.chdir(project_name)
        subprocess.check_call(["python", "manage.py", "tailwind", "init"])
        new_settings = settings.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'theme', \n    'tailwind',  ")

        with open(os.path.join(project_name, "settings.py"), "w") as file:
            file.write(new_settings)
        # subprocess.check_call(['python', 'manage.py', 'tailwind', 'install'])
    except subprocess.CalledProcessError as e:
        print(f"[❌ ERROR] Error during Tailwind initialization: {e}")
        return

    configure_tailwind(project_name)


def configure_tailwind(project_name):
    """Configures Tailwind for the project."""
    tailwind_config_path = os.path.join("theme/static_src", "tailwind.config.js")
    try:
        with open(tailwind_config_path, "r") as file:
            config = file.read()

        new_config = config.replace(
            "content: []", f"content: ['./{project_name}/**/*.html', './theme/static_src/**/*.js']"
        )

        with open(tailwind_config_path, "w") as file:
            file.write(new_config)

        print(
            "[✔️ INFO] Tailwind configuration updated.\n \n \n use python\
             manage.py tailwind install to install Tailwind \n use this command\
             to watch for changes: \n python manage.py tailwind start \n \n \n"
        )

    except FileNotFoundError:
        print(f"[❌ ERROR] Tailwind configuration file not found: {tailwind_config_path}")
