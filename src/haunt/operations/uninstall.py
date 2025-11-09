"""Uninstall operations."""

from pathlib import Path

from haunt.exceptions import PackageNotFoundError
from haunt.files import remove_empty_directories
from haunt.files import remove_symlink
from haunt.models import UninstallPlan
from haunt.registry import Registry


def compute_uninstall_plan(package_name: str, registry_path: Path) -> UninstallPlan:
    """Compute a plan for uninstalling a package.

    Args:
        package_name: Name of package to uninstall
        registry_path: Path to registry file

    Returns:
        UninstallPlan with symlinks to remove and any missing symlinks

    Raises:
        PackageNotFoundError: If package not found in registry
    """
    # Load registry and get package entry
    registry = Registry.load(registry_path)
    try:
        entry = registry.packages[package_name]
    except KeyError:
        raise PackageNotFoundError(f"Package '{package_name}' not found in registry")

    symlinks_to_remove = []
    missing_symlinks = []

    for symlink in entry.symlinks:
        # Check if symlink exists
        if symlink.link_path.exists(follow_symlinks=False):
            symlinks_to_remove.append(symlink)
        else:
            missing_symlinks.append(symlink.link_path)

    return UninstallPlan(
        package_name=package_name,
        target_dir=entry.target_dir,
        symlinks_to_remove=symlinks_to_remove,
        missing_symlinks=missing_symlinks,
    )


def execute_uninstall_plan(plan: UninstallPlan, registry_path: Path) -> None:
    """Execute an uninstall plan by removing symlinks and updating registry.

    Args:
        plan: UninstallPlan to execute
        registry_path: Path to registry file
    """
    # Remove all symlinks
    for symlink in plan.symlinks_to_remove:
        remove_symlink(symlink)

    # Clean up empty directories
    link_paths = [symlink.link_path for symlink in plan.symlinks_to_remove]
    remove_empty_directories(plan.target_dir, link_paths)

    # Update registry
    registry = Registry.load(registry_path)
    del registry.packages[plan.package_name]
    registry.save(registry_path)
