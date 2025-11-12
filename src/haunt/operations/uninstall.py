"""Uninstall operations."""

from haunt._files.cleanup import remove_empty_directories
from haunt._files.symlinks import remove_symlink
from haunt._registry import Registry
from haunt.exceptions import PackageNotFoundError
from haunt.models import UninstallPlan


def plan_uninstall(package_name: str) -> UninstallPlan:
    """Plan an uninstall operation.

    Args:
        package_name: Name of package to uninstall

    Returns:
        UninstallPlan with symlinks to remove and any missing symlinks

    Raises:
        PackageNotFoundError: If package not found in registry
    """
    registry = Registry()
    try:
        entry = registry.packages[package_name]
    except KeyError as e:
        raise PackageNotFoundError(
            f"Package '{package_name}' not found in registry"
        ) from e

    symlinks_to_remove = []
    missing_symlinks = []
    modified_symlinks = []

    for symlink in entry.symlinks:
        if not symlink.link_path.exists(follow_symlinks=False):
            missing_symlinks.append(symlink.link_path)
        elif symlink.exists():
            symlinks_to_remove.append(symlink)
        else:
            # Symlink exists but points to wrong target (user modified it)
            modified_symlinks.append(symlink)

    return UninstallPlan(
        package_name=package_name,
        target_dir=entry.target_dir,
        symlinks_to_remove=symlinks_to_remove,
        missing_symlinks=missing_symlinks,
        modified_symlinks=modified_symlinks,
    )


def apply_uninstall(plan: UninstallPlan) -> None:
    """Apply an uninstall plan by removing symlinks and updating registry.

    Args:
        plan: UninstallPlan to execute
    """
    for symlink in plan.symlinks_to_remove:
        remove_symlink(symlink)

    link_paths = [symlink.link_path for symlink in plan.symlinks_to_remove]
    remove_empty_directories(plan.target_dir, link_paths)

    registry = Registry()
    del registry.packages[plan.package_name]
    registry.save()
