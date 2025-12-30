"""
Rich console utilities for beautiful CLI output.
Provides centralized functions for formatted output, panels, tables, and more.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from typing import Optional, List, Dict, Any

# Singleton console instance
_console = Console()


# --- Unicode-safe output utilities for Windows compatibility ---

# Safe symbol alternatives for consoles that don't support Unicode
SAFE_SYMBOLS = {
    "✅": "[OK]",
    "❌": "[X]",
    "⚠": "[!]",
    "ℹ": "[i]",
    "✓": "[OK]",
    "✗": "[X]",
    "→": "->",
}


def _can_encode_unicode(text: str) -> bool:
    """Check if the current console can encode the given text.

    Args:
        text: Text to test encoding for

    Returns:
        True if text can be encoded, False otherwise
    """
    try:
        text.encode(sys.stdout.encoding or "utf-8")
        return True
    except (UnicodeEncodeError, LookupError, AttributeError):
        return False


def safe_text(text: str) -> str:
    """Replace Unicode symbols with safe ASCII alternatives if needed.

    Args:
        text: Text that may contain Unicode symbols

    Returns:
        Safe text with symbols replaced if console doesn't support them
    """
    if _can_encode_unicode(text):
        return text

    # Replace each Unicode symbol with its safe ASCII equivalent
    result = text
    for unicode_char, safe_char in SAFE_SYMBOLS.items():
        result = result.replace(unicode_char, safe_char)
    return result


def safe_print(message: str, **kwargs):
    """Print a message, replacing Unicode symbols with safe alternatives if needed.

    Args:
        message: Message to print (may contain Unicode symbols)
        **kwargs: Additional arguments passed to print()
    """
    print(safe_text(message), **kwargs)


def get_console() -> Console:
    """Get the singleton console instance."""
    return _console


def print_header(title: str, subtitle: str = ""):
    """Print a stylized header panel.

    Args:
        title: Main title text
        subtitle: Optional subtitle text
    """
    content = Text(title, style="bold bright_blue")
    if subtitle:
        content.append("\n", style="")
        content.append(subtitle, style="dim")
    _console.print(Panel(content, box=box.DOUBLE, border_style="bright_blue"))


def print_menu(menu_items: List[Dict[str, str]], title: str = "Main Menu"):
    """Print a menu using a rich table.

    Args:
        menu_items: List of dicts with 'key', 'label', and optional 'description'
        title: Menu title
    """
    table = Table(
        title=title,
        show_header=False,
        box=box.ROUNDED,
        border_style="bright_black",
        padding=(0, 1),
    )
    table.add_column(style="bold cyan", width=3)
    table.add_column(style="white")
    table.add_column(style="dim")

    for item in menu_items:
        key = item.get("key", "")
        label = item.get("label", "")
        description = item.get("description", "")
        table.add_row(key, label, description)

    _console.print(table)


def print_menu_simple(options: List[str], title: str = "Options"):
    """Print a simple numbered menu from a list of options.

    Args:
        options: List of option strings
        title: Menu title
    """
    table = Table(
        title=title,
        show_header=False,
        box=box.ROUNDED,
        border_style="bright_black",
        padding=(0, 1),
    )
    table.add_column(style="bold cyan", width=3)
    table.add_column(style="white")

    for i, option in enumerate(options, 1):
        table.add_row(str(i), option)

    _console.print(table)


def print_status(message: str, status: str = "info"):
    """Print a status message with appropriate styling.

    Args:
        message: The message to display
        status: Status type (info, success, warning, error)
    """
    status_styles = {
        "info": "[dim][i][/dim] ",
        "success": "[green][OK][/green] ",
        "warning": "[yellow][!][/yellow] ",
        "error": "[red][X][/red] ",
    }
    prefix = status_styles.get(status, status_styles["info"])
    style = {
        "info": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
    }.get(status, "white")

    _console.print(f"{prefix}[{style}]{message}[/{style}]")


def print_info(message: str):
    """Print an info message."""
    print_status(message, "info")


def print_success(message: str):
    """Print a success message."""
    print_status(message, "success")


def print_warning(message: str):
    """Print a warning message."""
    print_status(message, "warning")


def print_error(message: str):
    """Print an error message."""
    print_status(message, "error")


def print_section(title: str, style: str = "bold cyan"):
    """Print a section header.

    Args:
        title: Section title
        style: Style for the title text
    """
    _console.print(f"\n[{style}]{title}[/{style}]")


def print_divider(char: str = "─", style: str = "dim"):
    """Print a horizontal divider line.

    Args:
        char: Character to use for the divider
        style: Style for the divider
    """
    _console.print(f"[{style}]{char * _console.width}[/{style}]")


def print_kv_table(data: Dict[str, Any], title: str = ""):
    """Print a key-value table.

    Args:
        data: Dictionary of key-value pairs
        title: Optional table title
    """
    table = Table(title=title, show_header=True, box=box.SIMPLE)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    for key, value in data.items():
        table.add_row(str(key), str(value))

    _console.print(table)


def print_list(items: List[str], title: str = ""):
    """Print a bulleted list.

    Args:
        items: List of items to print
        title: Optional title
    """
    if title:
        print_section(title)
    for item in items:
        _console.print(f"  • {item}")


def confirm_action(prompt: str = "Continue?") -> bool:
    """Ask user for confirmation.

    Args:
        prompt: Confirmation prompt text

    Returns:
        True if user confirms, False otherwise
    """
    from rich.prompt import Confirm

    return Confirm.ask(prompt)


def input_prompt(prompt: str, default: Optional[str] = None) -> str:
    """Get user input with rich styling.

    Args:
        prompt: Prompt text
        default: Optional default value

    Returns:
        User input string
    """
    from rich.prompt import Prompt

    return Prompt.ask(prompt, default=default)


def clear_screen():
    """Clear the console screen."""
    import os

    _console.clear()
    os.system("cls" if os.name == "nt" else "clear")


def show_provider_status(status: Dict[str, Any]):
    """Display AI provider status in a formatted panel.

    Args:
        status: Dictionary with provider status information
    """
    provider_display = status["provider"].upper()
    if status["provider"] == "gemini":
        provider_display = "Google Gemini"
    elif status["provider"] == "openai":
        provider_display = "OpenAI-Compatible"

    key_status = (
        "[green][OK] Configured[/green]"
        if status["api_key_configured"]
        else "[red][X] Not configured[/red]"
    )

    content = f"""[bold]Provider:[/bold] {provider_display}
[bold]Model:[/bold] {status["model"]}
"""

    if status.get("base_url") and status["provider"] == "openai":
        content += f"[bold]Base URL:[/bold] {status['base_url']}\n"

    content += f"[bold]API Key:[/bold] {key_status}\n"

    if status["custom_prompts_loaded"]:
        content += f"[bold]Custom Prompts:[/bold] [green][OK] Loaded ({', '.join(status['custom_prompt_keys'])})[/green]"
    else:
        content += "[bold]Custom Prompts:[/bold] Using defaults"

    _console.print(Panel(content, title="[bold]AI Provider Status[/bold]", border_style="cyan"))


def show_settings_status(settings: Dict[str, str]):
    """Display current settings in a formatted panel.

    Args:
        settings: Dictionary of setting key-value pairs
    """
    content = ""
    for key, value in settings.items():
        content += f"[bold]{key}:[/bold] {value}\n"

    _console.print(Panel(content, title="[bold]Current Settings[/bold]", border_style="cyan"))


# --- Convenience wrappers matching task requirements ---


def confirm(question: str) -> bool:
    """Ask user for confirmation using rich.prompt.Confirm.

    Args:
        question: Confirmation question text

    Returns:
        True if user confirms, False otherwise
    """
    from rich.prompt import Confirm

    return Confirm.ask(question)


def ask(question: str, default: Optional[str] = None, password: bool = False) -> str:
    """Get user input using rich.prompt.Prompt.

    Args:
        question: Prompt question text
        default: Optional default value
        password: Whether to hide input (for passwords/secrets)

    Returns:
        User input string
    """
    from rich.prompt import Prompt

    return Prompt.ask(question, default=default, password=password)
