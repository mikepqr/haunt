"""Filesystem operations for haunt."""

from haunt.files.cleanup import remove_empty_directories
from haunt.files.discover import discover_files
from haunt.files.symlinks import check_conflict
from haunt.files.symlinks import create_symlink
from haunt.files.symlinks import remove_symlink

__all__ = [
    "check_conflict",
    "create_symlink",
    "discover_files",
    "remove_empty_directories",
    "remove_symlink",
]
