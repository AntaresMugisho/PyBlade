from pyblade.cli import BaseCommand, packages, tailwind
from pyblade.config import config


class Command(BaseCommand):
    """
    Install and configure Tailwind CSS in the current project.
    """

    name = "tailwind:config"
    aliases = ["tw:config"]  # Other possible names for the command

    def config(self):
        self.add_flag("--no-install", help="Configure the project without installing anything")

    def handle(self, **kwargs):
        """Execute the 'pyblade tailwind:config' command"""
        if config.path is None:
            self.error("This is not a PyBlade project: no pyblade.toml was found here or above.")
            return

        root = config.root
        manager = packages.js_manager(root)

        if not manager and not kwargs.get("no_install"):
            self.error(
                "Tailwind is installed with a JavaScript package manager, and none was found.\n"
                " Install Node, or run this again with --no-install and install it yourself:\n"
                f"   npm install {' '.join(tailwind.PACKAGES)}"
            )
            return

        if not kwargs.get("no_install"):
            with self.status(f"Installing Tailwind CSS with {manager}..."):
                command = packages.js_install_command(manager, tailwind.PACKAGES)
                result = packages.install(command, cwd=root)

            if result.returncode != 0:
                self.error(f"`{packages.as_typed(command)}` failed:\n{result.stderr.strip()}")
                return

            self.success(f"Installed {', '.join(tailwind.PACKAGES)}.")

        for done in tailwind.configure(root, config.paths.stubs, self._sources()):
            self.success(done, bold=False)

        config.stack.css_framework = "tailwindcss"
        config.stack.css_framework_version = "4"
        if manager:
            config.stack.js_package_manager = manager
        config.save()

        self.success("Tailwind CSS is configured.")
        self.tip("Run [blue]pyblade dev[/blue] to start the server and build your stylesheet as you work.")

    def _sources(self):
        """The directories Tailwind reads to find the classes a project uses."""
        directories = [config.paths.templates, config.paths.components]

        return [directory for directory in dict.fromkeys(directories) if directory]
