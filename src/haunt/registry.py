"""Registry operations for managing installed packages."""

import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Self

from platformdirs import user_state_path

from haunt.exceptions import RegistryValidationError
from haunt.exceptions import RegistryVersionError
from haunt.models import PackageEntry

REGISTRY_VERSION = 1


@dataclass
class Registry:
    """Registry of all installed packages."""

    version: int = REGISTRY_VERSION
    packages: dict[str, PackageEntry] = field(default_factory=dict)  # name -> entry

    @classmethod
    def default_path(cls) -> Path:
        """Get default registry location using platformdirs."""
        return user_state_path("haunt") / "registry.json"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "version": self.version,
            "packages": {
                name: entry.to_dict() for name, entry in self.packages.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """Create from dict loaded from JSON."""
        if "version" not in data:
            raise RegistryValidationError("Registry missing 'version' key")

        version = data["version"]
        if version > REGISTRY_VERSION:
            raise RegistryVersionError(
                f"Registry version {version} is newer than supported version {REGISTRY_VERSION}"
            )

        if "packages" not in data:
            raise RegistryValidationError("Registry missing 'packages' key")

        packages = {
            name: PackageEntry.from_dict(entry_data)
            for name, entry_data in data["packages"].items()
        }
        return cls(version=version, packages=packages)

    @classmethod
    def load(cls, path: Path | None = None) -> Self:
        """Load registry from JSON file. Creates empty if doesn't exist.

        Args:
            path: Path to registry file. If None, uses default location.
        """
        if path is None:
            path = cls.default_path()

        if not path.exists():
            return cls()

        try:
            data = json.loads(path.read_text())
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise RegistryValidationError(f"Invalid JSON in registry: {e}")
        except KeyError as e:
            raise RegistryValidationError(f"Missing required field in registry: {e}")

    def save(self, path: Path | None = None) -> None:
        """Save registry to JSON file atomically.

        Args:
            path: Path to save registry. If None, uses default location.
        """
        if path is None:
            path = self.default_path()

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically (write to temp file, then rename)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(self.to_dict(), indent=2))
        temp_path.replace(path)
