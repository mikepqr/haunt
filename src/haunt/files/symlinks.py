"""Symlink operations."""

from haunt.models import BrokenSymlinkConflict
from haunt.models import Conflict
from haunt.models import CorrectSymlinkConflict
from haunt.models import DifferentSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import FileConflict
from haunt.models import Symlink


def check_conflict(symlink: Symlink) -> Conflict | None:
    """Check if a symlink conflicts with existing files.

    Args:
        symlink: Symlink to check for conflicts (source_path should be absolute)

    Returns:
        Conflict if something exists at link_path, None if nothing exists.
        CorrectSymlinkConflict means symlink exists and points correctly.
    """
    # Nothing exists, no conflict
    if not symlink.link_path.exists() and not symlink.link_path.is_symlink():
        return None

    # Check if it's a symlink (even if broken)
    if symlink.link_path.is_symlink():
        actual_target = symlink.link_path.readlink()

        if symlink.exists():
            return CorrectSymlinkConflict(
                path=symlink.link_path,
                points_to=actual_target,
            )

        # Symlink points to wrong location - check if broken
        if not symlink.link_path.exists():
            return BrokenSymlinkConflict(
                path=symlink.link_path,
                points_to=actual_target,
            )

        # Symlink points to different location (but target exists)
        return DifferentSymlinkConflict(
            path=symlink.link_path,
            points_to=actual_target,
        )

    # It exists as something else - directory or file?
    if symlink.link_path.is_dir():
        return DirectoryConflict(path=symlink.link_path)
    else:
        return FileConflict(path=symlink.link_path)


def remove_symlink(symlink: Symlink) -> None:
    """Remove a symlink if it points to the expected source.

    Args:
        symlink: Symlink to remove (source_path should be absolute)

    Raises:
        FileNotFoundError: If link_path doesn't exist (from readlink or unlink)
        ValueError: If link_path points to wrong source
        OSError: If link_path is not a symlink (from readlink)
    """
    if symlink.exists():
        symlink.link_path.unlink()
    else:
        actual_target = symlink.link_path.readlink()
        raise ValueError(
            f"Symlink points to {actual_target}, expected {symlink.source_path}"
        )


def create_symlink(symlink: Symlink, force: bool = False) -> None:
    """Create a symlink.

    Args:
        symlink: Symlink to create (source_path should be absolute)
        force: If True, remove existing files/symlinks (but not directories)

    Raises:
        IsADirectoryError: If force=True and link_path is a directory
        FileExistsError: If something exists at link_path (filesystem changed after planning)
    """
    if symlink.exists():
        return

    # In force mode, remove existing files/symlinks (but not directories)
    if force:
        # Check if it's a real directory (is_dir follows symlinks, so we need both checks)
        if symlink.link_path.is_dir() and not symlink.link_path.is_symlink():
            raise IsADirectoryError(
                f"Cannot force-create symlink: {symlink.link_path} is a directory"
            )

        # Remove existing file or symlink if present (unlink removes link, not target)
        if symlink.link_path.exists() or symlink.link_path.is_symlink():
            symlink.link_path.unlink()

    # Create parent directories if needed
    symlink.link_path.parent.mkdir(parents=True, exist_ok=True)

    # Create the symlink with relative path
    symlink.link_path.symlink_to(symlink.relative_source_path)
