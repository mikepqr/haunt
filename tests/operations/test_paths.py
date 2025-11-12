"""Tests for path normalization utilities."""

from pathlib import Path

import pytest

from haunt._files.paths import validate_install_directories
from haunt.operations import normalize_package_dir
from haunt.operations import normalize_target_dir


class TestNormalizePackageDir:
    """Tests for normalize_package_dir()."""

    def test_resolves_to_absolute_path(self, tmp_path):
        """Test that relative paths are resolved to absolute."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Use relative path
        import os

        os.chdir(tmp_path)
        result = normalize_package_dir(Path("package"))

        assert result.is_absolute()
        assert result == package_dir.resolve()

    def test_already_absolute_path_unchanged(self, tmp_path):
        """Test that absolute paths are resolved (may resolve symlinks)."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        result = normalize_package_dir(package_dir)

        assert result.is_absolute()
        assert result == package_dir.resolve()

    def test_raises_for_nonexistent_directory(self, tmp_path):
        """Test that FileNotFoundError is raised for nonexistent path."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(FileNotFoundError, match="does not exist"):
            normalize_package_dir(nonexistent)

    def test_raises_for_file_not_directory(self, tmp_path):
        """Test that NotADirectoryError is raised for files."""
        package_file = tmp_path / "package.txt"
        package_file.write_text("content")

        with pytest.raises(NotADirectoryError, match="not a directory"):
            normalize_package_dir(package_file)


class TestNormalizeTargetDir:
    """Tests for normalize_target_dir()."""

    def test_resolves_to_absolute_path(self, tmp_path):
        """Test that relative paths are resolved to absolute."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Use relative path
        import os

        os.chdir(tmp_path)
        result = normalize_target_dir(Path("target"))

        assert result.is_absolute()
        assert result == target_dir.resolve()

    def test_already_absolute_path_unchanged(self, tmp_path):
        """Test that absolute paths are resolved (may resolve symlinks)."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = normalize_target_dir(target_dir)

        assert result.is_absolute()
        assert result == target_dir.resolve()

    def test_does_not_validate_existence(self, tmp_path):
        """Test that target_dir is not validated for existence."""
        nonexistent = tmp_path / "nonexistent"

        # Should not raise
        result = normalize_target_dir(nonexistent)

        assert result.is_absolute()


class TestValidateInstallDirectories:
    """Tests for validate_install_directories()."""

    def test_raises_when_package_is_root(self, tmp_path):
        """Test that package directory cannot be filesystem root."""
        target_dir = tmp_path / "target"

        with pytest.raises(
            ValueError, match="Package directory cannot be filesystem root"
        ):
            validate_install_directories(Path("/"), target_dir)

    def test_raises_when_target_equals_package(self, tmp_path):
        """Test that target and package directories cannot be the same."""
        package_dir = tmp_path / "package"

        with pytest.raises(ValueError, match="cannot be the same"):
            validate_install_directories(package_dir, package_dir)

    def test_raises_when_target_inside_package(self, tmp_path):
        """Test that target directory cannot be inside package directory."""
        package_dir = tmp_path / "package"
        target_dir = package_dir / "subdir"

        with pytest.raises(
            ValueError, match="Target directory cannot be inside package directory"
        ):
            validate_install_directories(package_dir, target_dir)

    def test_valid_directories_do_not_raise(self, tmp_path):
        """Test that valid directory configurations do not raise."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"

        # Should not raise
        validate_install_directories(package_dir, target_dir)
