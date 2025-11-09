"""Data models for haunt."""

from dataclasses import dataclass
from enum import Enum
from enum import auto
from pathlib import Path
from typing import Self


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


@dataclass
class PackageEntry:
    """Record of an installed package in the registry."""

    name: str  # Package identifier (basename of package directory)
    target_dir: Path  # Where symlinks were installed
    symlinks: list[Symlink]  # Symlinks that were created
    installed_at: str  # UTC ISO 8601 timestamp

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
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
    def from_dict(cls, data: dict) -> Self:
        """Create from dict loaded from JSON."""
        return cls(
            name=data["name"],
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


class ConflictType(Enum):
    """Type of conflict encountered."""

    FILE = auto()
    DIRECTORY = auto()
    CORRECT_SYMLINK = auto()
    DIFFERENT_SYMLINK = auto()
    BROKEN_SYMLINK = auto()


class ConflictMode(str, Enum):
    """How to handle conflicts when installing."""

    ABORT = "abort"
    SKIP = "skip"
    FORCE = "force"


@dataclass
class ConflictInfo:
    """Information about a file that conflicts with installation."""

    path: Path  # Full path to conflicting file in target
    type: ConflictType  # Type of conflict
    points_to: Path | None  # Where symlink points (only for SYMLINK type)


@dataclass
class InstallPlan:
    """Plan for what an install operation would do."""

    package_name: str
    package_dir: Path
    target_dir: Path
    symlinks_to_create: list[Symlink]
    conflicts: list[ConflictInfo]


@dataclass
class UninstallPlan:
    """Plan for what an uninstall operation would do."""

    package_name: str
    target_dir: Path
    symlinks_to_remove: list[Symlink]
    missing_symlinks: list[Path]  # Absolute paths to symlinks that don't exist
