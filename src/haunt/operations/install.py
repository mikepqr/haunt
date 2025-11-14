"""High-level operations for install and uninstall."""

from datetime import datetime
from pathlib import Path

from haunt._files.discover import discover_files
from haunt._files.paths import normalize_package_dir
from haunt._files.paths import normalize_target_dir
from haunt._files.paths import validate_install_directories
from haunt._files.symlinks import check_conflict
from haunt._files.symlinks import create_symlink
from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.models import Conflict
from haunt.models import ConflictMode
from haunt.models import CorrectSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import InstallPlan
from haunt.models import PackageEntry
from haunt.models import Symlink


def check_package_name_collision(package_name: str, package_dir: Path) -> None:
    """Raise if registry contains package_name installed from a different directory."""
    registry = Registry()
    if (
        package_name in registry.packages
        and registry.packages[package_name].package_dir != package_dir
    ):
        existing_entry = registry.packages[package_name]
        raise PackageAlreadyInstalledError(
            package_name=package_name,
            existing_path=str(existing_entry.package_dir),
            new_path=str(package_dir),
        )


def build_wanted_symlinks(package_dir: Path, target_dir: Path) -> list[Symlink]:
    """Build list of all symlinks that should exist after install."""
    files = discover_files(package_dir)
    return [
        Symlink(
            link_path=target_dir / rel_file_path,
            source_path=package_dir / rel_file_path,
        )
        for rel_file_path in files
    ]


def find_unwanted_symlinks(
    package_name: str,
    wanted_symlinks: list[Symlink],
) -> list[Symlink]:
    """Find symlinks from a previous install that should be removed."""
    registry = Registry()
    existing_entry = registry.packages.get(package_name)
    if existing_entry is None:
        return []
    else:
        # The set of symlinks haunt installed, and that have not been altered
        # since the installation.
        managed_symlinks = {r for r in existing_entry.symlinks if r.exists()}

        # Symlinks we manage, that are not wanted, should be removed.
        return list(managed_symlinks - set(wanted_symlinks))


def plan_install(
    package_dir: Path,
    target_dir: Path,
    on_conflict: ConflictMode = ConflictMode.ABORT,
) -> InstallPlan:
    """Plan an install operation.

    Args:
        package_dir: Directory containing files to symlink (will be resolved
            to absolute)
        target_dir: Directory where symlinks will be created (will be
            resolved to absolute)
        on_conflict: How to handle conflicts (ABORT, SKIP, or FORCE)

    Returns:
        InstallPlan with symlinks to create and any conflicts.
        - ABORT/SKIP: symlinks_to_create only contains non-conflicting files
        - FORCE: symlinks_to_create contains all files (conflicts will be replaced)

    Raises:
        FileNotFoundError: If package_dir does not exist
        NotADirectoryError: If package_dir is not a directory
        ValueError: If package_dir is /, or if target_dir equals or is inside
            package_dir
        PackageAlreadyInstalledError: If package name exists from different directory
    """
    package_dir = normalize_package_dir(package_dir)
    target_dir = normalize_target_dir(target_dir)
    validate_install_directories(package_dir, target_dir)

    package_name = package_dir.name
    check_package_name_collision(package_name, package_dir)

    wanted_symlinks = build_wanted_symlinks(package_dir, target_dir)

    symlinks_to_create: list[Symlink] = []
    conflicts: list[Conflict] = []

    # Find conflicts and symlinks to create
    for symlink in wanted_symlinks:
        conflict = check_conflict(symlink)
        if conflict is None:
            symlinks_to_create.append(symlink)
        else:
            conflicts.append(conflict)
            if (
                not isinstance(conflict, DirectoryConflict)
                and on_conflict == ConflictMode.FORCE
            ):
                symlinks_to_create.append(symlink)

    # Find managed symlinks that are no longer wanted
    symlinks_to_remove = find_unwanted_symlinks(package_name, wanted_symlinks)

    return InstallPlan(
        package_name=package_name,
        package_dir=package_dir,
        target_dir=target_dir,
        wanted_symlinks=wanted_symlinks,
        symlinks_to_create=symlinks_to_create,
        conflicts=conflicts,
        symlinks_to_remove=symlinks_to_remove,
    )


def apply_install(
    plan: InstallPlan,
    on_conflict: ConflictMode = ConflictMode.ABORT,
) -> None:
    """Apply an install plan by creating symlinks and updating registry.

    Args:
        plan: InstallPlan to execute
        on_conflict: How to handle conflicts (determines if force=True is used)

    Raises:
        PackageAlreadyInstalledError: If package name exists from different directory
        ConflictError: If directory conflicts exist (never replaceable)
        ConflictError: If on_conflict=ABORT and blocking conflicts exist
    """
    check_package_name_collision(plan.package_name, plan.package_dir)

    # Check for directory conflicts - these always block regardless of mode
    directory_conflicts = [
        c for c in plan.conflicts if isinstance(c, DirectoryConflict)
    ]
    if directory_conflicts:
        raise ConflictError(directory_conflicts)

    # Check for other blocking conflicts if ABORT mode
    if on_conflict == ConflictMode.ABORT:
        blocking_conflicts = [
            c for c in plan.conflicts if not isinstance(c, CorrectSymlinkConflict)
        ]
        if blocking_conflicts:
            raise ConflictError(blocking_conflicts)

    # Remove orphaned symlinks from previous install
    for symlink in plan.symlinks_to_remove:
        if symlink.link_path.is_symlink():
            symlink.link_path.unlink()

    # Create all symlinks (force=True in FORCE mode to replace existing files)
    force = on_conflict == ConflictMode.FORCE
    for symlink in plan.symlinks_to_create:
        create_symlink(symlink, force=force)

    # Build registry entry with all wanted symlinks
    entry = PackageEntry(
        name=plan.package_name,
        package_dir=plan.package_dir,
        target_dir=plan.target_dir,
        symlinks=plan.wanted_symlinks,
        installed_at=datetime.now().astimezone().isoformat(),
    )

    registry = Registry()
    registry.packages[plan.package_name] = entry
    registry.save()
