"""Tests for haunt registry operations."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import haunt._registry
from haunt._registry import REGISTRY_VERSION
from haunt._registry import Registry
from haunt.exceptions import RegistryValidationError
from haunt.exceptions import RegistryVersionError
from haunt.models import PackageEntry
from haunt.models import Symlink


class TestDefaultPath:
    """Tests for Registry.default_path()."""

    def test_default_path_calls_user_state_path(self, monkeypatch, tmp_path):
        """Test that default_path calls user_state_path('haunt')."""
        # Undo the autouse fixture monkeypatch to test the real implementation
        monkeypatch.undo()

        mock_user_state_path = MagicMock(return_value=tmp_path / "haunt_state")
        monkeypatch.setattr(haunt._registry, "user_state_path", mock_user_state_path)

        result = Registry.default_path()

        # Verify user_state_path was called with "haunt"
        mock_user_state_path.assert_called_once_with("haunt")

        # Verify the result is that path + "registry.json"
        assert result == tmp_path / "haunt_state" / "registry.json"


@pytest.fixture
def dotfiles_entry():
    """A standard dotfiles package entry for testing."""
    return PackageEntry(
        name="dotfiles",
        package_dir=Path("/home/user/dotfiles"),
        target_dir=Path("/home/user"),
        symlinks=[
            Symlink(
                link_path=Path("/home/user/.bashrc"),
                source_path=Path("/home/user/dotfiles/.bashrc"),
            ),
            Symlink(
                link_path=Path("/home/user/.vimrc"),
                source_path=Path("/home/user/dotfiles/.vimrc"),
            ),
        ],
        installed_at="2025-11-08T22:30:45.123456+00:00",
    )


@pytest.fixture
def nvim_entry():
    """A standard nvim package entry for testing."""
    return PackageEntry(
        name="nvim",
        package_dir=Path("/home/user/nvim-config"),
        target_dir=Path("/home/user"),
        symlinks=[
            Symlink(
                link_path=Path("/home/user/.config/nvim/init.vim"),
                source_path=Path("/home/user/nvim-config/.config/nvim/init.vim"),
            ),
        ],
        installed_at="2025-11-08T22:31:00.000000+00:00",
    )


class TestLoadRegistry:
    """Tests for Registry() constructor."""

    def test_load_nonexistent_file_creates_empty_registry(self, tmp_path):
        """Test loading when file doesn't exist returns empty registry."""
        registry_file = tmp_path / "registry.json"
        registry = Registry(path=registry_file)

        assert isinstance(registry, Registry)
        assert len(registry.packages) == 0
        assert registry.version == REGISTRY_VERSION

    def test_load_registry_with_no_packages(self, tmp_path):
        """Test loading file with empty packages dict."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps({"version": 1, "packages": {}}))

        registry = Registry(path=registry_file)

        assert len(registry.packages) == 0
        assert registry.version == 1

    def test_load_registry_with_packages(self, tmp_path, dotfiles_entry):
        """Test loading registry with existing packages."""
        registry_file = tmp_path / "registry.json"
        data = {
            "version": 1,
            "packages": {"dotfiles": dotfiles_entry.to_dict()},
        }
        registry_file.write_text(json.dumps(data))

        registry = Registry(path=registry_file)
        assert len(registry.packages) == 1
        assert registry.version == 1

        assert "dotfiles" in registry.packages
        assert registry.packages["dotfiles"].name == "dotfiles"
        assert registry.packages["dotfiles"].target_dir == Path("/home/user")
        assert len(registry.packages["dotfiles"].symlinks) == 2

    def test_load_registry_with_multiple_packages(
        self, tmp_path, dotfiles_entry, nvim_entry
    ):
        """Test loading registry with multiple packages."""
        registry_file = tmp_path / "registry.json"
        data = {
            "version": 1,
            "packages": {
                "dotfiles": dotfiles_entry.to_dict(),
                "nvim": nvim_entry.to_dict(),
            },
        }
        registry_file.write_text(json.dumps(data))

        registry = Registry(path=registry_file)

        assert len(registry.packages) == 2
        assert registry.version == 1
        assert "dotfiles" in registry.packages
        assert "nvim" in registry.packages

    def test_load_invalid_json_raises_error(self, tmp_path):
        """Test loading corrupted JSON raises RegistryValidationError."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{ invalid json }")

        with pytest.raises(RegistryValidationError):
            Registry(path=registry_file)

    def test_load_missing_packages_key_raises_error(self, tmp_path):
        """Test loading JSON without 'packages' key raises error."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps({"version": 1, "wrong_key": {}}))

        with pytest.raises(RegistryValidationError):
            Registry(path=registry_file)

    def test_load_missing_version_raises_error(self, tmp_path):
        """Test loading registry without version field raises error."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps({"packages": {}}))

        with pytest.raises(RegistryValidationError, match="missing 'version'"):
            Registry(path=registry_file)

    def test_load_future_version_raises_error(self, tmp_path):
        """Test loading registry with future version raises error."""
        registry_file = tmp_path / "registry.json"
        registry_file.write_text(json.dumps({"version": 999, "packages": {}}))

        with pytest.raises(RegistryVersionError, match="version 999"):
            Registry(path=registry_file)

    def test_load_with_none_uses_default_path(self, tmp_path, monkeypatch):
        """Test that Registry() with no path uses default_path()."""
        # Monkeypatch default_path to return a specific path
        test_registry = tmp_path / "test_registry.json"
        monkeypatch.setattr(Registry, "default_path", lambda cls: test_registry)

        # Create a registry file at the default path
        test_registry.write_text(json.dumps({"version": 1, "packages": {}}))

        # Registry() with no path should load from default_path
        registry = Registry()

        # Verify it loaded successfully (proving it read from the right path)
        assert registry.version == 1
        assert len(registry.packages) == 0

    def test_load_malformed_package_entry_raises_error(self, tmp_path):
        """Test that malformed package entry raises RegistryValidationError."""
        registry_file = tmp_path / "registry.json"
        # Package entry missing required 'name' field
        data = {
            "version": 1,
            "packages": {
                "broken": {
                    "target_dir": "/home/user",
                    # missing 'name', 'symlinks', 'installed_at'
                }
            },
        }
        registry_file.write_text(json.dumps(data))

        with pytest.raises(RegistryValidationError, match="Missing required field"):
            Registry(path=registry_file)


class TestSaveRegistry:
    """Tests for registry.save()."""

    def test_save_empty_registry(self, tmp_path):
        """Test saving an empty registry."""
        registry_file = tmp_path / "registry.json"
        registry = Registry(path=registry_file)

        registry.save()

        assert registry_file.exists()
        data = json.loads(registry_file.read_text())
        assert data == {"version": 1, "packages": {}}

    def test_save_registry_with_packages(self, tmp_path, dotfiles_entry):
        """Test saving registry with packages."""
        registry_file = tmp_path / "registry.json"
        registry = Registry(path=registry_file)
        registry.packages["dotfiles"] = dotfiles_entry

        registry.save()

        data = json.loads(registry_file.read_text())
        assert data["version"] == 1
        assert "dotfiles" in data["packages"]
        assert data["packages"]["dotfiles"]["name"] == "dotfiles"
        assert len(data["packages"]["dotfiles"]["symlinks"]) == 2

    def test_save_creates_parent_directories(self, tmp_path):
        """Test that save creates parent directories if needed."""
        registry_file = tmp_path / "nested" / "dir" / "registry.json"
        registry = Registry(path=registry_file)

        registry.save()

        assert registry_file.exists()
        assert registry_file.parent.exists()

    def test_save_roundtrip(self, tmp_path, dotfiles_entry):
        """Test that save/load roundtrip preserves data."""
        registry_file = tmp_path / "registry.json"
        original = Registry(path=registry_file)
        original.packages["dotfiles"] = dotfiles_entry

        original.save()
        loaded = Registry(path=registry_file)

        assert len(loaded.packages) == len(original.packages)
        assert "dotfiles" in loaded.packages
        assert loaded.packages["dotfiles"].name == "dotfiles"
        assert loaded.packages["dotfiles"].target_dir == Path("/home/user")
        assert len(loaded.packages["dotfiles"].symlinks) == 2
        assert loaded.packages["dotfiles"].symlinks[0].link_path == Path(
            "/home/user/.bashrc"
        )
        assert loaded.packages["dotfiles"].symlinks[0].source_path == Path(
            "/home/user/dotfiles/.bashrc"
        )

    def test_save_uses_constructor_path(self, tmp_path):
        """Test that save() uses path from constructor."""
        test_registry = tmp_path / "test_registry.json"

        # Create registry with specific path
        registry = Registry(path=test_registry)
        registry.save()

        # Verify the file was created at the specified path
        assert test_registry.exists()
        data = json.loads(test_registry.read_text())
        assert data == {"version": 1, "packages": {}}
