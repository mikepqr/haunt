"""High-level operations for haunt."""

from haunt.operations.install import compute_install_plan
from haunt.operations.install import execute_install_plan
from haunt.operations.paths import normalize_package_dir
from haunt.operations.paths import normalize_target_dir
from haunt.operations.uninstall import compute_uninstall_plan
from haunt.operations.uninstall import execute_uninstall_plan

__all__ = [
    "compute_install_plan",
    "compute_uninstall_plan",
    "execute_install_plan",
    "execute_uninstall_plan",
    "normalize_package_dir",
    "normalize_target_dir",
]
