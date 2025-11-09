"""File and directory discovery operations."""

from pathlib import Path


def discover_files(package_dir: Path) -> list[Path]:
    """Discover all files in package directory.

    Args:
        package_dir: Directory to scan for files

    Returns:
        Sorted list of relative paths to all files. Sorted for deterministic
        registry output (makes diffs/version control cleaner).
    """
    files = []
    for dirpath, dirnames, filenames in package_dir.walk():
        for filename in filenames:
            full_path = dirpath / filename
            rel_path = full_path.relative_to(package_dir)
            files.append(rel_path)

    return sorted(files)
