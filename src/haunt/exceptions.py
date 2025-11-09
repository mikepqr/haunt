"""Custom exceptions for haunt."""

from collections.abc import Sequence

from haunt.models import Conflict


class HauntError(Exception):
    """Base exception for haunt."""


class PackageNotFoundError(HauntError):
    """Package not found in registry or filesystem."""


class ConflictError(HauntError):
    """Conflicts exist and on_conflict=abort."""

    def __init__(self, conflicts: Sequence[Conflict]):
        self.conflicts = conflicts
        conflict_paths = ", ".join(str(c.path) for c in conflicts[:3])
        if len(conflicts) > 3:
            conflict_paths += f", ... ({len(conflicts)} total)"
        super().__init__(f"Conflicts detected: {conflict_paths}")


class InvalidPackageError(HauntError):
    """Package directory is invalid (empty, paths escape target, etc.)."""


class RegistryValidationError(HauntError):
    """Registry file is invalid or malformed."""


class RegistryVersionError(HauntError):
    """Registry version is unsupported."""
