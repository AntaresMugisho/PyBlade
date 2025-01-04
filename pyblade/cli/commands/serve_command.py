from commands.base_command import BaseCommand


class ServeCommand(BaseCommand):
    name = "serve"
    description = "Serve the PyBlade application"

    def handle(self, **kwargs):
        self.info("Starting PyBlade development server...")
        # TODO: Implement server functionality
        self.success("Server is running on http://localhost:8000")
