import click
import questionary
from questionary import Style as QStyle
from rich.console import Console
from rich.table import Table

# from pyblade.cli.command.add import liveblade
# from pyblade.cli.command.migrate import migrate

# Custom theme for questionary
custom_style = QStyle(
    [
        ("qmark", "fg:#673ab7 bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:#673ab7 bold"),  # submitted answer text behind the question
        ("pointer", "fg:yellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:#673ab7 bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:#673ab7"),  # style for a selected item of a checkbox
        ("separator", "fg:#cc5454"),  # separator in lists
        ("instruction", "fg:gray"),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:#858585 italic"),  # disabled choices for select and checkbox prompts
        ("placeholder", "fg:#858585 italic"),
    ]
)


class PyBladeCLI:
    def __init__(self):
        self.config = {"project_name": None, "framework": None, "css_framework": None, "use_liveblade": False}


class CommandGroup(click.Group):
    def format_help(self, ctx, formatter):
        console = Console()

        # Project header
        console.print(
            "\n[bold blue]PyBlade CLI[/bold blue]\n[italic] Modern Template Engine for Python web frameworks [/italic]"
        )

        # Group commands by category
        categories = {
            "Project Commands": ["init", "serve", "migrate"],
            "Generator Commands": ["make:component", "make:layout"],
            "Database Commands": ["db:migrate", "db:rollback", "db:seed", "db:reset", "db:refresh"],
            "Utility Commands": ["cache:clear", "view:clear"],
        }

        for category, commands in categories.items():
            table = Table(show_header=True, header_style="bold magenta", box=None)
            table.add_column("Command", style="cyan")
            table.add_column("Description", style="white")

            console.print(f"\n[bold yellow]{category}[/bold yellow]")

            for cmd_name in commands:
                cmd = self.get_command(ctx, cmd_name)
                if cmd:
                    table.add_row(cmd_name, cmd.help or "")

            console.print(table)

        console.print("\nUse [cyan]pyblade COMMAND --help[/cyan] for more information about a command.\n")


@click.group(cls=CommandGroup)
def cli():
    """PyBlade - Modern Template Engine for Python web frameworks"""
    pass


@cli.command()
def init():
    """Initialize a new PyBlade project"""

    answers = questionary.form(
        project_name=questionary.text("What is your project name?", default="my_project", style=custom_style),
        framework=questionary.select(
            "Which Python web framework would you like to use?",
            choices=["Django", "Flask"],
            style=custom_style,
        ),
        css_framework=questionary.select(
            "Would you like to install a CSS framework?",
            choices=["Tailwind CSS", "Bootstrap 5", questionary.Choice("Not sure", None)],
            style=custom_style,
        ),
        use_liveblade=questionary.select(
            "Would you like to use LiveBlade for interactive UI?",
            choices=[questionary.Choice("Yes", True), questionary.Choice("No", False)],
            style=custom_style,
        ),
    ).ask()

    # Save configuration
    blade = PyBladeCLI()
    blade.config.update(answers)

    print(blade.config)

    # framework = choose_framework()

    # ensure_django_installed()

    # print(f"[✔️ INFO] Creating a new Django project: {project_name}")
    # subprocess.check_call(['django-admin', 'startproject', project_name])

    # if questionary.confirm("Do you want to use liveBlade?").ask():
    #     configure_pyblade(project_name)

    # configure_framework(framework, project_name)

    # print("[🎉 SUCCESS] The Django project has been successfully initialized.")


if __name__ == "__main__":
    cli()
