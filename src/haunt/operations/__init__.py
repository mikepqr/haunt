"""High-level operations for haunt."""

from haunt.operations.install import apply_install
from haunt.operations.install import plan_install
from haunt.operations.uninstall import apply_uninstall
from haunt.operations.uninstall import plan_uninstall

__all__ = [
    "plan_install",
    "plan_uninstall",
    "apply_install",
    "apply_uninstall",
]
