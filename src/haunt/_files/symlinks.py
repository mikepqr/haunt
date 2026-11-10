"""Symlink operations."""

from collections.abc import Iterable
from pathlib import Path

from haunt.exceptions import StalePlanError
from haunt.models import LinkState
from haunt.models import Symlink


def observe(symlink: Symlink) -> LinkState:
    """Classify what currently occupies symlink.link_path."""
    link = symlink.link_path
    if not link.exists(follow_symlinks=False):
        if any(_is_non_directory(ancestor) for ancestor in link.parents):
            return LinkState.PARENT_NOT_DIRECTORY
        return LinkState.ABSENT
    if _is_same_entry(link, symlink.source_path):
        return LinkState.IS_SOURCE
    if link.is_symlink():
        if symlink.points_to(link.readlink()):
            return LinkState.CORRECT
        return LinkState.FOREIGN_LINK if link.exists() else LinkState.BROKEN_LINK
    return LinkState.DIRECTORY if link.is_dir() else LinkState.FILE


def _is_non_directory(path: Path) -> bool:
    """True for a file, or a symlink that does not lead to a directory."""
    return path.exists(follow_symlinks=False) and not path.is_dir()


def _is_same_entry(a: Path, b: Path) -> bool:
    """True if a and b name the same directory entry, not merely the same file."""
    return a.parent.resolve() / a.name == b.parent.resolve() / b.name


def ensure_unchanged(expected: Iterable[tuple[Symlink, LinkState]]) -> None:
    """Raise StalePlanError unless every symlink is still in its expected state.

    Plans are applied compare-and-swap: this runs before the first change, so
    a plan the filesystem has moved on from is rejected whole.
    """
    stale = [s.link_path for s, state in expected if observe(s) is not state]
    if stale:
        raise StalePlanError(stale)


def create_symlink(symlink: Symlink) -> None:
    """Create a relative symlink at link_path, making parent directories.

    Raises:
        FileExistsError: If something already exists at link_path
    """
    symlink.link_path.parent.mkdir(parents=True, exist_ok=True)
    symlink.link_path.symlink_to(symlink.relative_source_path)
