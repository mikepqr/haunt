"""High-level operations for install and uninstall."""

from datetime import datetime
from datetime import timezone
from pathlib import Path

from haunt.exceptions import ConflictError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.files import check_conflict
from haunt.files import create_symlink
from haunt.files import discover_files
from haunt.models import Conflict
from haunt.models import ConflictMode
from haunt.models import CorrectSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import InstallPlan
from haunt.models import PackageEntry
from haunt.models import Symlink
from haunt.operations.paths import normalize_package_dir
from haunt.operations.paths import normalize_target_dir
from haunt.operations.paths import validate_install_directories
from haunt.registry import Registry


def compute_install_plan(
    package_dir: Path, target_dir: Path, on_conflict: ConflictMode = ConflictMode.ABORT
) -> InstallPlan:
    """Compute a plan for installing a package.

    Args:
        package_dir: Directory containing files to symlink (will be resolved to absolute)
        target_dir: Directory where symlinks will be created (will be resolved to absolute)
        on_conflict: How to handle conflicts (ABORT, SKIP, or FORCE)

    Returns:
        InstallPlan with symlinks to create and any conflicts.
        - ABORT/SKIP: symlinks_to_create only contains non-conflicting files
        - FORCE: symlinks_to_create contains all files (conflicts will be replaced)

    Raises:
        FileNotFoundError: If package_dir does not exist
        NotADirectoryError: If package_dir is not a directory
        ValueError: If package_dir is /, or if target_dir equals or is inside package_dir
    """
    # Normalize paths to absolute
    package_dir = normalize_package_dir(package_dir)
    target_dir = normalize_target_dir(target_dir)

    # Validate directory relationships
    validate_install_directories(package_dir, target_dir)

    package_name = package_dir.name
    symlinks_to_create: list[Symlink] = []
    conflicts: list[Conflict] = []

    # Discover all files in the package
    files = discover_files(package_dir)

    for rel_file_path in files:
        # Compute paths (both absolute)
        source_path = package_dir / rel_file_path
        link_path = target_dir / rel_file_path

        # Create symlink with absolute paths
        symlink = Symlink(
            link_path=link_path,
            source_path=source_path,
        )

        # Check for conflicts
        conflict = check_conflict(symlink)
        if conflict is None:
            # Nothing exists, always create symlink
            symlinks_to_create.append(symlink)
        elif isinstance(conflict, CorrectSymlinkConflict):
            # Symlink already correct, never recreate
            conflicts.append(conflict)
        else:
            # Real conflict - record it for reporting
            conflicts.append(conflict)
            # In FORCE mode, replace non-directory conflicts
            if on_conflict == ConflictMode.FORCE and not isinstance(
                conflict, DirectoryConflict
            ):
                symlinks_to_create.append(symlink)

    return InstallPlan(
        package_name=package_name,
        package_dir=package_dir,
        target_dir=target_dir,
        symlinks_to_create=symlinks_to_create,
        conflicts=conflicts,
    )


def execute_install_plan(
    plan: InstallPlan,
    registry_path: Path,
    on_conflict: ConflictMode = ConflictMode.ABORT,
) -> None:
    """Execute an install plan by creating symlinks and updating registry.

    Args:
        plan: InstallPlan to execute
        registry_path: Path to registry file
        on_conflict: How to handle conflicts (determines if force=True is used)

    Raises:
        PackageAlreadyInstalledError: If package name exists from different directory
        ConflictError: If directory conflicts exist (never replaceable)
        ConflictError: If on_conflict=ABORT and blocking conflicts exist
    """
    # Check for package name uniqueness
    registry = Registry.load(registry_path)
    if plan.package_name in registry.packages:
        existing_entry = registry.packages[plan.package_name]
        if existing_entry.package_dir != plan.package_dir:
            raise PackageAlreadyInstalledError(
                package_name=plan.package_name,
                existing_path=str(existing_entry.package_dir),
                new_path=str(plan.package_dir),
            )

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

    # Create all symlinks (force=True in FORCE mode to replace existing files)
    force = on_conflict == ConflictMode.FORCE
    for symlink in plan.symlinks_to_create:
        create_symlink(symlink, force=force)

    # Build list of all symlinks for registry (created + already correct)
    all_symlinks = plan.symlinks_to_create.copy()
    for conflict in plan.conflicts:
        if isinstance(conflict, CorrectSymlinkConflict):
            # Reconstruct symlink from conflict info
            # We need to resolve points_to to get the absolute source path
            absolute_source = (conflict.path.parent / conflict.points_to).resolve()
            all_symlinks.append(
                Symlink(link_path=conflict.path, source_path=absolute_source)
            )

    # Create package entry
    entry = PackageEntry(
        name=plan.package_name,
        package_dir=plan.package_dir,
        target_dir=plan.target_dir,
        symlinks=all_symlinks,
        installed_at=datetime.now(timezone.utc).isoformat(),
    )

    # Update registry (reuse registry loaded earlier)
    registry.packages[plan.package_name] = entry
    registry.save(registry_path)
