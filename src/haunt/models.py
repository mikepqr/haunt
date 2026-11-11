"""Data models for haunt."""

from dataclasses import dataclass
from enum import Enum
from enum import StrEnum
from enum import auto
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


@dataclass(frozen=True)
class Symlink:
    """A symlink to create or manage."""

    link_path: Path  # Where the symlink will be created (absolute)
    source_path: Path  # What the symlink points to (absolute)

    @property
    def relative_source_path(self) -> Path:
        """Get source_path relative to the directory that really contains link_path.

        The OS resolves a relative symlink against the real location of its
        directory, not the path used to reach it, so symlinked ancestors of
        link_path must be resolved first.
        """
        return self.source_path.relative_to(
            self.link_path.parent.resolve(), walk_up=True
        )

    def points_to(self, target: Path) -> bool:
        """Check if target points to the same location as source_path.

        Args:
            target: Path to compare (can be relative or absolute)

        Returns:
            True if target and source_path resolve to the same location
        """
        target_resolved = (self.link_path.parent / target).resolve()
        return target_resolved == self.source_path.resolve()


@dataclass
class PackageEntry:
    """Record of an installed package in the registry."""

    name: str  # Package identifier (basename of package directory)
    package_dir: Path  # Absolute path to package directory
    target_dir: Path  # Where symlinks were installed
    symlinks: list[Symlink]  # Symlinks that were created
    installed_at: str  # ISO 8601 timestamp with UTC offset

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


class LinkState(Enum):
    """What currently occupies a Symlink's link_path.

    Every operation (install, uninstall, list) starts from this one
    classification, made by haunt._files.symlinks.observe().
    """

    ABSENT = auto()  # Nothing there
    CORRECT = auto()  # Symlink to source_path
    FOREIGN_LINK = auto()  # Symlink to something else that exists
    BROKEN_LINK = auto()  # Symlink to something else that does not exist
    FILE = auto()
    DIRECTORY = auto()
    # link_path is the package file itself, reached through a directory that
    # is symlinked into the package (e.g. left behind by GNU stow's folding).
    # Removing it would delete the source.
    IS_SOURCE = auto()
    # An ancestor of link_path exists but is not a directory, so no link can
    # be created there.
    PARENT_NOT_DIRECTORY = auto()


class Action(Enum):
    """What install does about one wanted symlink."""

    CREATE = auto()
    REPLACE = auto()  # Remove whatever is at link_path, then create
    KEEP = auto()  # Already correct
    SKIP = auto()  # Leave the conflicting path alone and carry on
    BLOCK = auto()  # Refuse to install


class ConflictMode(StrEnum):
    """How to handle conflicts when installing."""

    ABORT = "abort"
    SKIP = "skip"
    FORCE = "force"


@dataclass(frozen=True)
class PlannedLink:
    """A wanted symlink, the state it was found in, and what to do about it."""

    symlink: Symlink
    state: LinkState
    action: Action


@dataclass
class InstallPlan:
    """Plan for what an install operation would do.

    plan_install() never returns a plan containing Action.BLOCK.
    """

    package_name: str
    package_dir: Path
    target_dir: Path
    links: list[PlannedLink]  # One per symlink that should exist after install
    symlinks_to_remove: list[Symlink]  # Orphaned symlinks from previous install


@dataclass
class UninstallPlan:
    """Plan for what an uninstall operation would do."""

    package_name: str
    target_dir: Path
    symlinks_to_remove: list[Symlink]
    missing_symlinks: list[Path]  # Absolute paths to symlinks that don't exist
    modified_symlinks: list[Symlink]  # No longer haunt's link; left alone
