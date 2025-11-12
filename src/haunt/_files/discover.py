"""File and directory discovery operations."""

import subprocess
from pathlib import Path


def _should_use_git(package_dir: Path) -> bool:
    """Check if package directory is in a git repository.

    Args:
        package_dir: Directory to check

    Returns:
        True if git repo detected, False otherwise
    """
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=package_dir,
            capture_output=True,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def discover_files_walk(package_dir: Path) -> list[Path]:
    """Discover all files in package directory using filesystem walk.

    Args:
        package_dir: Directory to scan for files

    Returns:
        Sorted list of relative paths to all files. Sorted for deterministic
        registry output (makes diffs/version control cleaner).
    """
    files = []
    for dirpath, _dirnames, filenames in package_dir.walk():
        for filename in filenames:
            full_path = dirpath / filename
            rel_path = full_path.relative_to(package_dir)
            files.append(rel_path)

    return sorted(files)


def discover_files_git(package_dir: Path) -> list[Path]:
    """Discover tracked files in git repository using git ls-files.

    Args:
        package_dir: Directory to scan for files (must be in a git repo)

    Returns:
        Sorted list of relative paths to all tracked files, excluding
        .gitmodules. Includes files in submodules.
    """
    result = subprocess.run(
        ["git", "ls-files", "-z", "--recurse-submodules"],
        cwd=package_dir,
        capture_output=True,
        check=True,
        text=True,
    )

    files = []
    for file_str in result.stdout.split("\0"):
        if not file_str:  # Skip empty strings from trailing null
            continue
        file_path = Path(file_str)
        if file_path.name == ".gitmodules":
            continue
        files.append(file_path)

    return sorted(files)


def discover_files(package_dir: Path) -> list[Path]:
    """Discover all files in package directory.

    Uses git ls-files if package is in a git repository (respects .gitignore,
    includes submodules, excludes .gitmodules). Falls back to filesystem walk
    otherwise.

    Args:
        package_dir: Directory to scan for files

    Returns:
        Sorted list of relative paths to all files. Sorted for deterministic
        registry output (makes diffs/version control cleaner).
    """
    if _should_use_git(package_dir):
        return discover_files_git(package_dir)
    return discover_files_walk(package_dir)
