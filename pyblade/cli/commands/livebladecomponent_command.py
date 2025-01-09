from ..commands.base_command import BaseCommand


class LivebladeComponentCommand(BaseCommand):
    name = "liveblade:component"
    description = "Create a new LiveBlade component"
    arguments = ["name"]
    options = {
        "directory": {
            "help": "Optional destination directory",
            "default": "liveblade",
        },
        "template": {
            "help": "Template to use for the component",
            "default": None,
        },
        "state": {
            "help": "Add state management to the component",
            "is_flag": True,
            "default": False,
        },
    }

    def handle(self, **kwargs):
        """Create a new LiveBlade component."""
        pass  # Logic to be implemented
