"""High-level operations for haunt."""

from haunt._files.paths import normalize_package_dir
from haunt._files.paths import normalize_target_dir
from haunt.operations.install import apply_install
from haunt.operations.install import plan_install
from haunt.operations.uninstall import apply_uninstall
from haunt.operations.uninstall import plan_uninstall

__all__ = [
    "plan_install",
    "plan_uninstall",
    "apply_install",
    "apply_uninstall",
    "normalize_package_dir",
    "normalize_target_dir",
]
