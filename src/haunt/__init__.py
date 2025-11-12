"""Haunt: Symlink dotfiles manager."""

from importlib.metadata import version

from haunt.operations import apply_install
from haunt.operations import apply_uninstall
from haunt.operations import plan_install
from haunt.operations import plan_uninstall

__version__ = version("haunt")

__all__ = [
    "plan_install",
    "apply_install",
    "plan_uninstall",
    "apply_uninstall",
]
