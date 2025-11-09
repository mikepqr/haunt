"""Cleanup operations."""

from pathlib import Path


def remove_empty_directories(target_dir: Path, file_paths: list[Path]) -> list[Path]:
    """Remove empty directories after removing symlinks.

    Walks up from each file's parent directory, removing empty directories
    until hitting a non-empty one or target_dir.

    Args:
        target_dir: Base directory (won't be removed, stops walking here)
        file_paths: Absolute paths of files that were removed

    Returns:
        List of absolute paths to directories that were removed

    Raises:
        ValueError: If any file_path is not under target_dir
    """
    removed = []
    checked = set()  # Track directories we've already processed

    for file_path in file_paths:
        # Validate that file_path is under target_dir
        try:
            file_path.relative_to(target_dir)
        except ValueError:
            raise ValueError(f"{file_path} is not under {target_dir}")

        # Get the parent directory of this file
        current = file_path.parent

        # Walk up the directory tree
        while current != target_dir:
            # Skip if we've already checked this directory
            if current in checked:
                break
            checked.add(current)

            # Skip if directory doesn't exist
            if not current.exists():
                break

            # Try to remove the directory (only works if empty)
            try:
                current.rmdir()
                removed.append(current)
                # Move up to parent
                current = current.parent
            except OSError:
                # Directory not empty, stop walking up this branch
                break

    return removed
