"""Uninstall operations."""

from haunt._files.cleanup import remove_empty_directories
from haunt._files.symlinks import ensure_unchanged
from haunt._files.symlinks import observe
from haunt._registry import Registry
from haunt.exceptions import PackageNotFoundError
from haunt.models import LinkState
from haunt.models import UninstallPlan

_MISSING = (LinkState.ABSENT, LinkState.PARENT_NOT_DIRECTORY)


def plan_uninstall(package_name: str) -> UninstallPlan:
    """Plan an uninstall operation. Changes nothing on disk.

    Only symlinks that are still exactly as haunt left them are removed.

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

    states = {symlink: observe(symlink) for symlink in entry.symlinks}
    return UninstallPlan(
        package_name=package_name,
        target_dir=entry.target_dir,
        symlinks_to_remove=[s for s in states if states[s] is LinkState.CORRECT],
        missing_symlinks=[s.link_path for s in states if states[s] in _MISSING],
        modified_symlinks=[
            s for s in states if states[s] not in (LinkState.CORRECT, *_MISSING)
        ],
    )


def apply_uninstall(plan: UninstallPlan) -> None:
    """Apply an uninstall plan by removing symlinks and updating registry.

    Raises:
        StalePlanError: If the filesystem changed since the plan was made
    """
    ensure_unchanged((s, LinkState.CORRECT) for s in plan.symlinks_to_remove)

    link_paths = [symlink.link_path for symlink in plan.symlinks_to_remove]
    for link_path in link_paths:
        link_path.unlink()
    remove_empty_directories(plan.target_dir, link_paths)

    registry = Registry()
    del registry.packages[plan.package_name]
    registry.save()
