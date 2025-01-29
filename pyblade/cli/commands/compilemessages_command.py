from .django_command import DjangoCommand


class CompileMessagesCommand(DjangoCommand):
    name = "compile:messages"
    description = "Compile translation files"
    django_command = "compilemessages"
    aliases = ["messages:compile"]
    options = {
        "locale": {
            "help": "Locale(s) to process (e.g. de_AT)",
            "multiple": True,
        },
        "exclude": {
            "help": "Locales to exclude",
            "multiple": True,
        },
        "use-fuzzy": {
            "help": "Use fuzzy translations",
            "is_flag": True,
            "default": False,
        },
    }

    def handle(self, **kwargs):
        """Compile translation files."""
        pass  # Logic to be implemented
