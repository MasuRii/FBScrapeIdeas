"""
CLI package for FB Scrape Ideas.
"""

from .menu_handler import run_cli, create_arg_parser
from .console import (
    print_header,
    print_menu,
    print_status,
    print_info,
    print_success,
    print_warning,
    print_error,
    clear_screen,
)

__all__ = [
    "run_cli",
    "create_arg_parser",
    "print_header",
    "print_menu",
    "print_status",
    "print_info",
    "print_success",
    "print_warning",
    "print_error",
    "clear_screen",
]
