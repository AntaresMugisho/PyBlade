from commands.base_command import PyBladeCommand
from core.exceptions import PyBladeException
from prompts.project_prompts import ProjectPrompts
from services.project.configurator import ProjectConfigurator
from services.project.creator import ProjectCreator


class InitCommand(PyBladeCommand):
    name = "init"
    description = "Create a new PyBlade project"
    options = {
        "name": {"help": "Project name"},
        "framework": {"type": click.Choice(["django", "flask"]), "help": "Framework to use"},
    }

    def handle(self, **kwargs):
        try:
            # Get project configuration
            project_data = ProjectPrompts.get_project_info(
                default_name=kwargs.get("name"), default_framework=kwargs.get("framework")
            )

            # Initialize services
            creator = ProjectCreator()
            configurator = ProjectConfigurator()

            # Create project
            self.info("Creating project structure...")
            creator.create_project(project_data)

            # Configure project
            self.info("Configuring project...")
            configurator.configure(project_data)

            self.success(f"Project {project_data['name']} created successfully!")

        except PyBladeException as e:
            self.error(str(e))
            return 1
        except Exception as e:
            self.error(f"Unexpected error: {str(e)}")
            return 1
