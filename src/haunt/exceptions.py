"""Custom exceptions for haunt."""

from collections.abc import Sequence

from haunt.models import Conflict


class HauntError(Exception):
    """Base exception for haunt."""


class PackageNotFoundError(HauntError):
    """Package not found in registry or filesystem."""


class PackageAlreadyInstalledError(HauntError):
    """Package with same name is already installed."""

    def __init__(self, package_name: str, existing_path: str, new_path: str):
        self.package_name = package_name
        self.existing_path = existing_path
        self.new_path = new_path
        super().__init__(
            f"Package '{package_name}' is already installed from {existing_path}.\n\n"
            f"To install from {new_path}, either:\n"
            f"  - Uninstall first: haunt uninstall {package_name}\n"
            f"  - Rename the directory (e.g., mv {new_path} {new_path}-alt)"
        )


class ConflictError(HauntError):
    """Conflicts exist and on_conflict=abort."""

    def __init__(self, conflicts: Sequence[Conflict]):
        self.conflicts = conflicts
        conflict_paths = ", ".join(str(c.path) for c in conflicts[:3])
        if len(conflicts) > 3:
            conflict_paths += f", ... ({len(conflicts)} total)"
        super().__init__(f"Conflicts detected: {conflict_paths}")


class RegistryValidationError(HauntError):
    """Registry file is invalid or malformed."""


class RegistryVersionError(HauntError):
    """Registry version is unsupported."""
