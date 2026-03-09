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
        if not file_path.is_relative_to(target_dir):
            raise ValueError(f"{file_path} is not under {target_dir}")

        current = file_path.parent
        while current != target_dir:
            if current in checked:
                break
            checked.add(current)

            try:
                current.rmdir()
                removed.append(current)
                current = current.parent
            except OSError:
                # Directory not empty or doesn't exist, stop walking up
                break

    return removed
