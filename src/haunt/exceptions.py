"""Custom exceptions for haunt."""

from collections.abc import Iterable
from collections.abc import Sequence
from pathlib import Path

from haunt.models import PlannedLink


def _summarize(paths: Iterable[Path]) -> str:
    """List the first few paths, with a total if there are more."""
    paths = list(paths)
    shown = ", ".join(str(p) for p in paths[:3])
    return f"{shown}, ... ({len(paths)} total)" if len(paths) > 3 else shown


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
    """Existing paths block the install under the chosen conflict mode."""

    def __init__(self, conflicts: Sequence[PlannedLink]):
        self.conflicts = conflicts
        super().__init__(
            f"Conflicts detected: {_summarize(c.symlink.link_path for c in conflicts)}"
        )


class StalePlanError(HauntError):
    """The filesystem no longer matches what a plan observed."""

    def __init__(self, paths: Sequence[Path]):
        self.paths = paths
        super().__init__(
            f"Filesystem changed since planning, nothing was done: {_summarize(paths)}"
        )


class RegistryValidationError(HauntError):
    """Registry file is invalid or malformed."""


class RegistryVersionError(HauntError):
    """Registry version is unsupported."""
