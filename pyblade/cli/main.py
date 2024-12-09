import sys
from colorama import Fore, Style
from pyblade.cli.command.migrate import migrate
from pyblade.cli.command.add import liveblade
from pyblade.cli.command.init_ import init

COMMANDS = {
    "migrate": {
        "function": migrate,
        "description": "Migrete your Django project to PyBlade.",
        "aliases": ["-m"]
    },
    "add liveblade": {
        "function": liveblade,
        "description": "Add Liveblade to your project if your need  use the directive liveBlade.",
        "aliases": ["-l", "add-lb"]
    },
    "init": {
        "function": init,
        "description": "Initialize the project with necessary files.",
        "aliases": ["init", "start"]
    }
}

def get_command_from_alias(alias):
    """Return the main command corresponding to an alias."""
    for cmd, details in COMMANDS.items():
        if alias == cmd or alias in details.get("aliases", []):
            return cmd
    return None

def display_help():
    """Display help for available commands, including their aliases."""
    print(f"{Fore.CYAN}Available commands:{Style.RESET_ALL}")
    for cmd, details in COMMANDS.items():
        aliases = ", ".join(details.get("aliases", []))
        description = details["description"]
        alias_info = f" (Aliases: {Fore.YELLOW}{aliases}{Style.RESET_ALL})" if aliases else ""
        print(f"  - {Fore.YELLOW}{cmd}{Style.RESET_ALL}: {description}{alias_info}")
    print(f"\nUse {Fore.GREEN}'python pyblade <command>'{Style.RESET_ALL} to execute a command.")
    print(f"Example: {Fore.GREEN}python pyblade add liveblade{Style.RESET_ALL}")

def cli():
    """Execute the corresponding function based on command-line arguments."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        display_help()
        return

    action = " ".join(sys.argv[1:])
    command = get_command_from_alias(action)  
    if command:
        try:
            COMMANDS[command]["function"]()
        except Exception as e:
            print(f"{Fore.RED}Error executing the command '{command}': {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Command '{action}' not recognized.{Style.RESET_ALL}")
        display_help()

if __name__ == '__main__':
    cli()
