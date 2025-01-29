from .django_command import DjangoCommand


class MakeMessagesCommand(DjangoCommand):
    name = "make:messages"
    description = "Create or update translation files"
    django_command = "makemessages"
    options = {
        "locale": {
            "help": "Locale(s) to process (e.g. en_US)",
            "multiple": True,
        },
        "exclude": {
            "help": "Locales to exclude",
            "multiple": True,
        },
        "all": {
            "help": "Process all available locales",
            "is_flag": True,
            "default": False,
        },
        "extension": {
            "help": "File extension(s) to examine (default: html,py)",
            "multiple": True,
            "default": ["html", "py"],
        },
        "ignore": {
            "help": "Ignore directories matching this glob-style pattern",
            "multiple": True,
        },
        "no-location": {
            "help": "Do not write location comments",
            "is_flag": True,
            "default": False,
        },
    }

    def handle(self, **kwargs):
        """Create or update translation files."""
        pass  # Logic to be implemented
