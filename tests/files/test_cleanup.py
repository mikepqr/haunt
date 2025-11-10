"""Tests for filesystem cleanup operations."""

import pytest

from haunt.files import remove_empty_directories


class TestRemoveEmptyDirectories:
    """Tests for remove_empty_directories()."""

    def test_no_directories_removed_when_none_empty(self, tmp_path):
        """Test that no directories are removed when they're not empty."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create directory with a file that stays
        config_dir = target_dir / ".config"
        config_dir.mkdir()
        (config_dir / "other.txt").write_text("content")

        # Remove a different file from the same directory
        removed_files = [target_dir / ".config" / "removed.txt"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert removed_dirs == []
        assert config_dir.exists()

    def test_removes_empty_directory(self, tmp_path):
        """Test that an empty directory is removed."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        config_dir = target_dir / ".config"
        config_dir.mkdir()

        removed_files = [target_dir / ".config" / "file.txt"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert config_dir in removed_dirs
        assert not config_dir.exists()

    def test_removes_nested_empty_directories(self, tmp_path):
        """Test that nested empty directories are removed."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        nvim_dir = target_dir / ".config" / "nvim" / "plugin"
        nvim_dir.mkdir(parents=True)

        removed_files = [target_dir / ".config" / "nvim" / "plugin" / "file.vim"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert nvim_dir in removed_dirs
        assert target_dir / ".config" / "nvim" in removed_dirs
        assert target_dir / ".config" in removed_dirs
        assert not (target_dir / ".config").exists()

    def test_stops_removing_at_non_empty_directory(self, tmp_path):
        """Test that removal stops when hitting a non-empty directory."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        config_dir = target_dir / ".config"
        config_dir.mkdir()
        (config_dir / "other.txt").write_text("content")

        nvim_dir = config_dir / "nvim"
        nvim_dir.mkdir()

        removed_files = [target_dir / ".config" / "nvim" / "init.vim"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert nvim_dir in removed_dirs
        assert config_dir not in removed_dirs
        assert config_dir.exists()
        assert not nvim_dir.exists()

    def test_does_not_remove_target_directory(self, tmp_path):
        """Test that target_dir itself is never removed."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        removed_files = [target_dir / "file.txt"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert removed_dirs == []
        assert target_dir.exists()

    def test_handles_multiple_files_in_different_directories(self, tmp_path):
        """Test removing directories for multiple files."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        (target_dir / ".config").mkdir()
        (target_dir / "bin").mkdir()

        removed_files = [
            target_dir / ".config" / "settings.json",
            target_dir / "bin" / "script.sh",
        ]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        assert target_dir / ".config" in removed_dirs
        assert target_dir / "bin" in removed_dirs
        assert not (target_dir / ".config").exists()
        assert not (target_dir / "bin").exists()

    def test_handles_empty_file_list(self, tmp_path):
        """Test that empty file list results in no directories removed."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        removed_dirs = remove_empty_directories(target_dir, [])

        assert removed_dirs == []

    def test_ignores_nonexistent_directories(self, tmp_path):
        """Test that nonexistent directories don't cause errors."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Directory doesn't actually exist
        removed_files = [target_dir / ".config" / "nvim" / "init.vim"]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        # Should not raise, just return empty list
        assert removed_dirs == []

    def test_raises_error_for_file_outside_target_dir(self, tmp_path):
        """Test that ValueError is raised if file is not under target_dir."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create a file path outside target_dir
        other_dir = tmp_path / "other"
        outside_file = other_dir / "file.txt"

        with pytest.raises(ValueError, match="is not under"):
            remove_empty_directories(target_dir, [outside_file])

    def test_handles_duplicate_paths_efficiently(self, tmp_path):
        """Test that already-checked directories are skipped (optimization)."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        config_dir = target_dir / ".config"
        config_dir.mkdir()

        # Two files in the same directory - second should trigger "already checked"
        removed_files = [
            target_dir / ".config" / "file1.txt",
            target_dir / ".config" / "file2.txt",
        ]

        removed_dirs = remove_empty_directories(target_dir, removed_files)

        # Should only remove .config once
        assert config_dir in removed_dirs
        assert removed_dirs.count(config_dir) == 1
        assert not config_dir.exists()
