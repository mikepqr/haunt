"""Filesystem operations for haunt."""

from haunt._files.cleanup import remove_empty_directories
from haunt._files.discover import discover_files
from haunt._files.symlinks import check_conflict
from haunt._files.symlinks import create_symlink
from haunt._files.symlinks import remove_symlink

__all__ = [
    "check_conflict",
    "create_symlink",
    "discover_files",
    "remove_empty_directories",
    "remove_symlink",
]
