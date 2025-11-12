"""Tests for symlink operations."""

from pathlib import Path

import pytest

from haunt._files.symlinks import check_conflict
from haunt._files.symlinks import create_symlink
from haunt._files.symlinks import remove_symlink
from haunt.models import BrokenSymlinkConflict
from haunt.models import CorrectSymlinkConflict
from haunt.models import DifferentSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import FileConflict
from haunt.models import Symlink


class TestSymlink:
    """Tests for Symlink dataclass methods."""

    def test_relative_source_path(self, tmp_path):
        """Test that relative_source_path returns correct relative path."""
        link_path = tmp_path / "target" / "file.txt"
        source_path = tmp_path / "package" / "file.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        assert symlink.relative_source_path == Path("../package/file.txt")

    def test_relative_source_path_nested(self, tmp_path):
        """Test relative_source_path with nested directories."""
        link_path = tmp_path / "target" / "config" / "nvim" / "init.vim"
        source_path = tmp_path / "package" / "config" / "nvim" / "init.vim"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        assert symlink.relative_source_path == Path(
            "../../../package/config/nvim/init.vim"
        )

    def test_points_to_with_relative_path(self, tmp_path):
        """Test points_to with a relative path target."""
        link_path = tmp_path / "target" / "file.txt"
        source_path = tmp_path / "package" / "file.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        # Should match when given the relative path
        assert symlink.points_to(Path("../package/file.txt"))

    def test_points_to_with_absolute_path(self, tmp_path):
        """Test points_to with an absolute path target."""
        link_path = tmp_path / "target" / "file.txt"
        source_path = tmp_path / "package" / "file.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        # Should match when given the absolute path
        assert symlink.points_to(source_path)

    def test_points_to_returns_false_for_different_path(self, tmp_path):
        """Test points_to returns False for different paths."""
        link_path = tmp_path / "target" / "file.txt"
        source_path = tmp_path / "package" / "file.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        # Should not match a different path
        assert not symlink.points_to(Path("../other/file.txt"))

    def test_points_to_handles_symlinks_in_path(self, tmp_path):
        """Test points_to works even with symlinks in the path."""
        # Create a symlinked directory
        real_dir = tmp_path / "real_package"
        real_dir.mkdir()
        link_dir = tmp_path / "package"
        link_dir.symlink_to(real_dir)

        link_path = tmp_path / "target" / "file.txt"
        source_path = tmp_path / "package" / "file.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        # Should resolve through the symlink
        assert symlink.points_to(Path("../real_package/file.txt"))

    def test_is_missing_when_link_doesnt_exist(self, tmp_path):
        """Test is_missing returns True when link doesn't exist."""
        link_path = tmp_path / "nonexistent.txt"
        source_path = tmp_path / "source.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        assert symlink.is_missing()

    def test_is_missing_returns_false_when_link_exists(self, tmp_path):
        """Test is_missing returns False when link exists."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(source)

        symlink = Symlink(link_path=link, source_path=source)

        assert not symlink.is_missing()

    def test_is_modified_when_link_points_wrong(self, tmp_path):
        """Test is_modified returns True when link points to wrong target."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        other = tmp_path / "other.txt"
        other.write_text("other")
        link = tmp_path / "link.txt"
        link.symlink_to(other)  # Point to other, not source

        symlink = Symlink(link_path=link, source_path=source)

        assert symlink.is_modified()

    def test_is_modified_returns_false_when_correct(self, tmp_path):
        """Test is_modified returns False when link is correct."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(source)

        symlink = Symlink(link_path=link, source_path=source)

        assert not symlink.is_modified()

    def test_is_modified_returns_false_when_missing(self, tmp_path):
        """Test is_modified returns False when link doesn't exist."""
        link_path = tmp_path / "nonexistent.txt"
        source_path = tmp_path / "source.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        assert not symlink.is_modified()

    def test_source_exists_when_file_exists(self, tmp_path):
        """Test source_exists returns True when source file exists."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link_path = tmp_path / "link.txt"

        symlink = Symlink(link_path=link_path, source_path=source)

        assert symlink.source_exists()

    def test_source_exists_returns_false_when_missing(self, tmp_path):
        """Test source_exists returns False when source doesn't exist."""
        source_path = tmp_path / "nonexistent.txt"
        link_path = tmp_path / "link.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)

        assert not symlink.source_exists()

    def test_get_actual_target_returns_target(self, tmp_path):
        """Test get_actual_target returns the symlink target."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(source)

        symlink = Symlink(link_path=link, source_path=source)

        assert symlink.get_actual_target() == source

    def test_get_actual_target_returns_none_for_non_symlink(self, tmp_path):
        """Test get_actual_target returns None for non-symlink."""
        regular_file = tmp_path / "file.txt"
        regular_file.write_text("content")
        source_path = tmp_path / "source.txt"

        symlink = Symlink(link_path=regular_file, source_path=source_path)

        assert symlink.get_actual_target() is None


class TestCheckConflict:
    """Tests for check_conflict()."""

    def test_no_conflict_when_path_does_not_exist(self, tmp_path):
        """Test that no conflict is returned when path doesn't exist."""
        symlink = Symlink(
            link_path=tmp_path / "nonexistent.txt",
            source_path=tmp_path / "source.txt",
        )

        conflict = check_conflict(symlink)

        assert conflict is None

    def test_already_correct_when_symlink_points_to_correct_location(self, tmp_path):
        """Test that CORRECT_SYMLINK when symlink already points to expected source."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link_path = tmp_path / "link.txt"
        link_path.symlink_to(source)

        symlink = Symlink(link_path=link_path, source_path=source)
        conflict = check_conflict(symlink)

        assert conflict is not None
        assert isinstance(conflict, CorrectSymlinkConflict)
        assert conflict.path == link_path
        assert conflict.points_to == source

    def test_conflict_when_regular_file_exists(self, tmp_path):
        """Test that conflict is detected for existing regular file."""
        link_path = tmp_path / "existing.txt"
        link_path.write_text("content")
        source_path = tmp_path / "source.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)
        conflict = check_conflict(symlink)

        assert conflict is not None
        assert isinstance(conflict, FileConflict)
        assert conflict.path == link_path

    def test_conflict_when_symlink_points_to_wrong_location(self, tmp_path):
        """Test that conflict is detected when symlink points elsewhere."""
        wrong_source = tmp_path / "wrong.txt"
        wrong_source.write_text("content")
        link_path = tmp_path / "link.txt"
        link_path.symlink_to(wrong_source)

        expected_source = tmp_path / "correct.txt"
        symlink = Symlink(link_path=link_path, source_path=expected_source)
        conflict = check_conflict(symlink)

        assert conflict is not None
        assert isinstance(conflict, DifferentSymlinkConflict)
        assert conflict.path == link_path
        assert conflict.points_to == wrong_source

    def test_conflict_for_broken_symlink(self, tmp_path):
        """Test that conflict is detected for broken symlink."""
        nonexistent_source = tmp_path / "nonexistent.txt"
        link_path = tmp_path / "broken_link.txt"
        link_path.symlink_to(nonexistent_source)

        expected_source = tmp_path / "correct.txt"
        symlink = Symlink(link_path=link_path, source_path=expected_source)
        conflict = check_conflict(symlink)

        assert conflict is not None
        assert isinstance(conflict, BrokenSymlinkConflict)
        assert conflict.path == link_path
        assert conflict.points_to == nonexistent_source

    def test_conflict_when_directory_exists(self, tmp_path):
        """Test that conflict is detected when a directory exists at path."""
        link_path = tmp_path / "dir"
        link_path.mkdir()
        source_path = tmp_path / "source.txt"

        symlink = Symlink(link_path=link_path, source_path=source_path)
        conflict = check_conflict(symlink)

        assert conflict is not None
        assert isinstance(conflict, DirectoryConflict)
        assert conflict.path == link_path


class TestRemoveSymlink:
    """Tests for remove_symlink()."""

    def test_remove_symlink_with_correct_target(self, tmp_path):
        """Test removing a symlink that points to expected target."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(source)

        symlink = Symlink(link_path=link, source_path=source)
        remove_symlink(symlink)

        assert not link.exists()
        assert source.exists()  # Source file still exists

    def test_raises_when_target_does_not_match(self, tmp_path):
        """Test that ValueError is raised when symlink points to wrong target."""
        wrong_source = tmp_path / "wrong.txt"
        wrong_source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(wrong_source)

        expected_source = tmp_path / "expected.txt"
        symlink = Symlink(link_path=link, source_path=expected_source)

        with pytest.raises(ValueError, match="Symlink points to"):
            remove_symlink(symlink)

        assert link.exists()  # Symlink still exists

    def test_raises_when_path_does_not_exist(self, tmp_path):
        """Test that FileNotFoundError is raised for nonexistent path."""
        nonexistent = tmp_path / "nonexistent.txt"
        source = tmp_path / "source.txt"

        symlink = Symlink(link_path=nonexistent, source_path=source)

        with pytest.raises(FileNotFoundError):
            remove_symlink(symlink)

    def test_raises_for_regular_file(self, tmp_path):
        """Test that OSError is raised for regular files."""
        regular_file = tmp_path / "file.txt"
        regular_file.write_text("content")
        source = tmp_path / "source.txt"

        symlink = Symlink(link_path=regular_file, source_path=source)

        with pytest.raises(OSError):
            remove_symlink(symlink)

        assert regular_file.exists()

    def test_removes_broken_symlink(self, tmp_path):
        """Test that broken symlinks can be removed."""
        nonexistent = tmp_path / "nonexistent.txt"
        link = tmp_path / "broken_link.txt"
        link.symlink_to(nonexistent)

        symlink = Symlink(link_path=link, source_path=nonexistent)
        remove_symlink(symlink)

        assert not link.exists()


class TestCreateSymlink:
    """Tests for create_symlink()."""

    def test_creates_new_symlink(self, tmp_path):
        """Test creating a new symlink."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"

        symlink = Symlink(link_path=link, source_path=source)
        create_symlink(symlink)

        assert link.is_symlink()
        assert symlink.points_to(link.readlink())

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created if needed."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "nested" / "dirs" / "link.txt"

        symlink = Symlink(link_path=link, source_path=source)
        create_symlink(symlink)

        assert link.is_symlink()
        assert symlink.points_to(link.readlink())
        assert link.parent.exists()

    def test_no_op_when_symlink_already_correct(self, tmp_path):
        """Test that it's a no-op when symlink already points correctly."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.symlink_to(source)

        symlink = Symlink(link_path=link, source_path=source)
        create_symlink(symlink)

        # Should not raise and link should still point to same place
        assert link.readlink() == source

    def test_raises_when_file_exists_without_force(self, tmp_path):
        """Test that FileExistsError is raised when file exists and force=False."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.write_text("existing file")

        symlink = Symlink(link_path=link, source_path=source)

        with pytest.raises(FileExistsError):
            create_symlink(symlink, force=False)

    def test_replaces_file_with_force(self, tmp_path):
        """Test that existing file is replaced when force=True."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link.txt"
        link.write_text("existing file")

        symlink = Symlink(link_path=link, source_path=source)
        create_symlink(symlink, force=True)

        assert link.is_symlink()
        assert symlink.points_to(link.readlink())

    def test_replaces_wrong_symlink_with_force(self, tmp_path):
        """Test that wrong symlink is replaced when force=True."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        wrong_source = tmp_path / "wrong.txt"
        wrong_source.write_text("wrong")
        link = tmp_path / "link.txt"
        link.symlink_to(wrong_source)

        symlink = Symlink(link_path=link, source_path=source)
        create_symlink(symlink, force=True)

        assert link.is_symlink()
        assert symlink.points_to(link.readlink())
        # Verify it points to correct source
        assert link.resolve() == source.resolve()

    def test_raises_for_directory_even_with_force(self, tmp_path):
        """Test that IsADirectoryError is raised for directory even with force=True."""
        source = tmp_path / "source.txt"
        source.write_text("content")
        link = tmp_path / "link_dir"
        link.mkdir()

        symlink = Symlink(link_path=link, source_path=source)

        with pytest.raises(IsADirectoryError):
            create_symlink(symlink, force=True)
