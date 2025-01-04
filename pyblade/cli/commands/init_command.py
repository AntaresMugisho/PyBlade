from commands.base_command import BaseCommand
from exceptions import PyBladeException
from services.project_service import ProjectService


class InitCommand(BaseCommand):
    name = "init"
    description = "Create a new PyBlade project"

    def handle(self, **kwargs):
        try:
            # Initialize services
            service = ProjectService()

            # Get project configuration
            project_data = service.get_project_info()

            # Create project
            self.info("Creating project structure...")

            # Configure project
            self.info("Configuring project...")

            self.success(f"Project {project_data['name']} created successfully!")

        except PyBladeException as e:
            self.error(str(e))
            return 1
        except Exception as e:
            self.error(f"Unexpected error: {str(e)}")
            return 1
