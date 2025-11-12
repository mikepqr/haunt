"""Data models for haunt."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Self
from typing import TypedDict


class SymlinkDict(TypedDict):
    """JSON-serializable representation of a Symlink."""

    link_path: str
    source_path: str


class PackageEntryDict(TypedDict):
    """JSON-serializable representation of a PackageEntry."""

    name: str
    package_dir: str
    target_dir: str
    symlinks: list[SymlinkDict]
    installed_at: str


@dataclass
class Symlink:
    """A symlink to create or manage."""

    link_path: Path  # Where the symlink will be created (absolute)
    source_path: Path  # What the symlink points to (absolute)

    @property
    def relative_source_path(self) -> Path:
        """Get source_path as relative to link_path's parent."""
        return self.source_path.relative_to(self.link_path.parent, walk_up=True)

    def points_to(self, target: Path) -> bool:
        """Check if target points to the same location as source_path.

        Args:
            target: Path to compare (can be relative or absolute)

        Returns:
            True if target and source_path resolve to the same location
        """
        target_resolved = (self.link_path.parent / target).resolve()
        return target_resolved == self.source_path.resolve()

    def exists(self) -> bool:
        """Check if link_path exists as a symlink pointing to source_path.

        Returns:
            True if link_path is a symlink that points to source_path
        """
        if not self.link_path.is_symlink():
            return False
        actual_target = self.link_path.readlink()
        return self.points_to(actual_target)

    def is_missing(self) -> bool:
        """Check if the symlink doesn't exist at link_path.

        Returns:
            True if link_path doesn't exist at all
        """
        return not self.link_path.exists(follow_symlinks=False)

    def is_modified(self) -> bool:
        """Check if symlink exists but points to wrong target.

        Returns:
            True if link_path exists but doesn't point to source_path
        """
        return self.link_path.exists(follow_symlinks=False) and not self.exists()

    def source_exists(self) -> bool:
        """Check if the source file exists.

        Returns:
            True if source_path exists
        """
        return self.source_path.exists()

    def get_actual_target(self) -> Path | None:
        """Get the actual target the symlink points to.

        Returns:
            The path the symlink points to, or None if link_path is not a symlink
        """
        if not self.link_path.is_symlink():
            return None
        return self.link_path.readlink()


@dataclass
class PackageEntry:
    """Record of an installed package in the registry."""

    name: str  # Package identifier (basename of package directory)
    package_dir: Path  # Absolute path to package directory
    target_dir: Path  # Where symlinks were installed
    symlinks: list[Symlink]  # Symlinks that were created
    installed_at: str  # UTC ISO 8601 timestamp

    def to_dict(self) -> PackageEntryDict:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "package_dir": str(self.package_dir),
            "target_dir": str(self.target_dir),
            "symlinks": [
                {
                    "link_path": str(s.link_path),
                    "source_path": str(s.source_path),
                }
                for s in self.symlinks
            ],
            "installed_at": self.installed_at,
        }

    @classmethod
    def from_dict(cls, data: PackageEntryDict) -> Self:
        """Create from dict loaded from JSON."""
        return cls(
            name=data["name"],
            package_dir=Path(data["package_dir"]),
            target_dir=Path(data["target_dir"]),
            symlinks=[
                Symlink(
                    link_path=Path(s["link_path"]),
                    source_path=Path(s["source_path"]),
                )
                for s in data["symlinks"]
            ],
            installed_at=data["installed_at"],
        )


@dataclass
class FileConflict:
    """Conflict with a regular file."""

    path: Path


@dataclass
class DirectoryConflict:
    """Conflict with a directory."""

    path: Path


@dataclass
class CorrectSymlinkConflict:
    """Conflict with a symlink that points to the correct target."""

    path: Path
    points_to: Path  # Where the symlink currently points (relative)


@dataclass
class BrokenSymlinkConflict:
    """Conflict with a broken symlink."""

    path: Path
    points_to: Path  # Where the symlink points (relative, but target doesn't exist)


@dataclass
class DifferentSymlinkConflict:
    """Conflict with a symlink pointing to a different target."""

    path: Path
    points_to: Path  # Where the symlink currently points (relative)


# Union type for all conflict types
Conflict = (
    FileConflict
    | DirectoryConflict
    | CorrectSymlinkConflict
    | BrokenSymlinkConflict
    | DifferentSymlinkConflict
)


class ConflictMode(str, Enum):
    """How to handle conflicts when installing."""

    ABORT = "abort"
    SKIP = "skip"
    FORCE = "force"


@dataclass
class InstallPlan:
    """Plan for what an install operation would do."""

    package_name: str
    package_dir: Path
    target_dir: Path
    symlinks_to_create: list[Symlink]
    conflicts: list[Conflict]


@dataclass
class UninstallPlan:
    """Plan for what an uninstall operation would do."""

    package_name: str
    target_dir: Path
    symlinks_to_remove: list[Symlink]
    missing_symlinks: list[Path]  # Absolute paths to symlinks that don't exist
    modified_symlinks: list[Symlink]  # Symlinks that exist but point to wrong target
