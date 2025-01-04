from rich.console import Console
from rich.panel import Panel

console = Console()


def display_success(message: str, title: str = None):
    """Display success message in panel"""
    console.print(Panel.fit(f"✨ {message}", title=title, style="bold green"))


def display_error(message: str, title: str = None):
    """Display error message in panel"""
    console.print(Panel.fit(f"❌ {message}", title=title, style="bold red"))
