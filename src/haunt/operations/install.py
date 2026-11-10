"""Install operations."""

from datetime import datetime
from pathlib import Path

from haunt._files.cleanup import remove_empty_directories
from haunt._files.discover import discover_files
from haunt._files.paths import normalize_package_dir
from haunt._files.paths import validate_install_directories
from haunt._files.symlinks import create_symlink
from haunt._files.symlinks import ensure_unchanged
from haunt._files.symlinks import observe
from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.models import Action
from haunt.models import ConflictMode
from haunt.models import InstallPlan
from haunt.models import LinkState
from haunt.models import PackageEntry
from haunt.models import PlannedLink
from haunt.models import Symlink

# The only things install will ever remove to make way for a symlink.
_REPLACEABLE = frozenset(
    {LinkState.FILE, LinkState.FOREIGN_LINK, LinkState.BROKEN_LINK}
)


def decide(state: LinkState, on_conflict: ConflictMode) -> Action:
    """Decide what install does about a wanted symlink found in the given state.

    This is the whole conflict policy; nothing else chooses an Action.
    """
    if state is LinkState.ABSENT:
        return Action.CREATE
    if state is LinkState.CORRECT:
        return Action.KEEP
    if on_conflict is ConflictMode.SKIP:
        return Action.SKIP
    if on_conflict is ConflictMode.FORCE and state in _REPLACEABLE:
        return Action.REPLACE
    return Action.BLOCK


def plan_link(symlink: Symlink, on_conflict: ConflictMode) -> PlannedLink:
    """Observe a wanted symlink and decide what to do about it."""
    state = observe(symlink)
    return PlannedLink(symlink, state, decide(state, on_conflict))


def check_package_name_collision(
    registry: Registry, package_name: str, package_dir: Path
) -> None:
    """Raise if registry contains package_name installed from a different directory."""
    existing_entry = registry.packages.get(package_name)
    if existing_entry is not None and existing_entry.package_dir != package_dir:
        raise PackageAlreadyInstalledError(
            package_name=package_name,
            existing_path=str(existing_entry.package_dir),
            new_path=str(package_dir),
        )


def build_wanted_symlinks(package_dir: Path, target_dir: Path) -> list[Symlink]:
    """Build list of all symlinks that should exist after install."""
    return [
        Symlink(
            link_path=target_dir / rel_file_path,
            source_path=package_dir / rel_file_path,
        )
        for rel_file_path in discover_files(package_dir)
    ]


def find_unwanted_symlinks(
    existing_entry: PackageEntry | None,
    wanted_symlinks: list[Symlink],
) -> list[Symlink]:
    """Find symlinks from a previous install that should be removed.

    Only symlinks that are still exactly as haunt left them qualify; anything
    the user has since changed is no longer ours to remove.
    """
    if existing_entry is None:
        return []
    wanted = set(wanted_symlinks)
    return [
        symlink
        for symlink in existing_entry.symlinks
        if symlink not in wanted and observe(symlink) is LinkState.CORRECT
    ]


def plan_install(
    package_dir: Path,
    target_dir: Path,
    on_conflict: ConflictMode = ConflictMode.ABORT,
) -> InstallPlan:
    """Plan an install operation. Changes nothing on disk.

    Args:
        package_dir: Directory containing files to symlink (will be resolved
            to absolute)
        target_dir: Directory where symlinks will be created (will be
            resolved to absolute)
        on_conflict: How to handle conflicts (ABORT, SKIP, or FORCE)

    Returns:
        InstallPlan that apply_install() can carry out in full.

    Raises:
        FileNotFoundError: If package_dir does not exist
        NotADirectoryError: If package_dir is not a directory
        ValueError: If package_dir is /, or if target_dir equals or is inside
            package_dir
        PackageAlreadyInstalledError: If package name exists from different directory
        ConflictError: If existing paths block the install under on_conflict
    """
    package_dir = normalize_package_dir(package_dir)
    target_dir = target_dir.resolve()
    validate_install_directories(package_dir, target_dir)

    package_name = package_dir.name
    registry = Registry()
    check_package_name_collision(registry, package_name, package_dir)

    wanted_symlinks = build_wanted_symlinks(package_dir, target_dir)
    links = [plan_link(symlink, on_conflict) for symlink in wanted_symlinks]
    blocked = [link for link in links if link.action is Action.BLOCK]
    if blocked:
        raise ConflictError(blocked)

    return InstallPlan(
        package_name=package_name,
        package_dir=package_dir,
        target_dir=target_dir,
        links=links,
        symlinks_to_remove=find_unwanted_symlinks(
            registry.packages.get(package_name), wanted_symlinks
        ),
    )


def apply_install(plan: InstallPlan) -> None:
    """Apply an install plan by creating symlinks and updating registry.

    Raises:
        PackageAlreadyInstalledError: If package name exists from different directory
        StalePlanError: If the filesystem changed since the plan was made
    """
    registry = Registry()
    check_package_name_collision(registry, plan.package_name, plan.package_dir)
    ensure_unchanged(
        [(link.symlink, link.state) for link in plan.links]
        + [(symlink, LinkState.CORRECT) for symlink in plan.symlinks_to_remove]
    )

    for symlink in plan.symlinks_to_remove:
        symlink.link_path.unlink()
    remove_empty_directories(
        plan.target_dir, [symlink.link_path for symlink in plan.symlinks_to_remove]
    )

    for link in plan.links:
        if link.action is Action.REPLACE:
            link.symlink.link_path.unlink()
        if link.action in (Action.CREATE, Action.REPLACE):
            create_symlink(link.symlink)

    registry.packages[plan.package_name] = PackageEntry(
        name=plan.package_name,
        package_dir=plan.package_dir,
        target_dir=plan.target_dir,
        symlinks=[link.symlink for link in plan.links],
        installed_at=datetime.now().astimezone().isoformat(),
    )
    registry.save()
