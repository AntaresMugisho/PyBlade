from commands.base_command import BaseCommand
from utils.runner import command


class ServeCommand(BaseCommand):
    name = "serve"
    description = "Serve the Django application"

    def handle(self, **kwargs):
        command("python manage.py runserver")
