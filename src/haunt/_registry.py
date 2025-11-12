"""Registry operations for managing installed packages."""

import json
from pathlib import Path
from typing import TypedDict

from platformdirs import user_state_path

from haunt.exceptions import RegistryValidationError
from haunt.exceptions import RegistryVersionError
from haunt.models import PackageEntry
from haunt.models import PackageEntryDict

REGISTRY_VERSION = 1


class RegistryDict(TypedDict):
    """JSON-serializable representation of a Registry."""

    version: int
    packages: dict[str, PackageEntryDict]


class Registry:
    """Registry of all installed packages."""

    def __init__(self, path: Path | None = None):
        """Load registry from path, or create empty if doesn't exist.

        Args:
            path: Path to registry file. If None, uses default location.
        """
        self.path = path if path is not None else self.default_path()
        self.version = REGISTRY_VERSION
        self.packages: dict[str, PackageEntry] = {}

        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                self._load_from_dict(data)
            except json.JSONDecodeError as e:
                raise RegistryValidationError(f"Invalid JSON in registry: {e}") from e
            except KeyError as e:
                raise RegistryValidationError(
                    f"Missing required field in registry: {e}"
                ) from e

    @classmethod
    def default_path(cls) -> Path:
        """Get default registry location using platformdirs."""
        return user_state_path("haunt") / "registry.json"

    def _load_from_dict(self, data: RegistryDict) -> None:
        """Load registry data from dict."""
        if "version" not in data:
            raise RegistryValidationError("Registry missing 'version' key")

        self.version = data["version"]
        if self.version > REGISTRY_VERSION:
            raise RegistryVersionError(
                f"Registry version {self.version} is newer than supported version "
                f"{REGISTRY_VERSION}"
            )

        if "packages" not in data:
            raise RegistryValidationError("Registry missing 'packages' key")

        self.packages = {
            name: PackageEntry.from_dict(entry_data)
            for name, entry_data in data["packages"].items()
        }

    def to_dict(self) -> RegistryDict:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "packages": {
                name: entry.to_dict() for name, entry in self.packages.items()
            },
        }

    def save(self) -> None:
        """Save registry to JSON file atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temp file
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.to_dict(), indent=2))
        temp_path.replace(self.path)
