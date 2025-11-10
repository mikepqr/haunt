"""Path normalization and validation utilities."""

from pathlib import Path


def normalize_package_dir(package_dir: Path) -> Path:
    """Normalize and validate package directory path.

    Args:
        package_dir: Directory containing files to symlink

    Returns:
        Absolute path to package directory

    Raises:
        FileNotFoundError: If package_dir does not exist
        NotADirectoryError: If package_dir is not a directory
    """
    package_dir = package_dir.resolve()

    if not package_dir.exists():
        raise FileNotFoundError(f"Package directory does not exist: {package_dir}")
    if not package_dir.is_dir():
        raise NotADirectoryError(f"Package path is not a directory: {package_dir}")

    return package_dir


def normalize_target_dir(target_dir: Path) -> Path:
    """Normalize target directory path to absolute.

    Args:
        target_dir: Directory where symlinks will be created

    Returns:
        Absolute path to target directory
    """
    return target_dir.resolve()
