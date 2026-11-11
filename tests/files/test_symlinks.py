"""Tests for symlink operations."""

from pathlib import Path

import pytest

from haunt._files.symlinks import create_symlink
from haunt._files.symlinks import ensure_unchanged
from haunt._files.symlinks import observe
from haunt.exceptions import StalePlanError
from haunt.models import LinkState
from haunt.models import Symlink


class TestSymlink:
    """Tests for Symlink path arithmetic."""

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

    @pytest.mark.parametrize("real_dir", ["real", "deeply/nested/real"])
    def test_relative_source_path_reaches_source_through_symlinked_directory(
        self, tmp_path, real_dir
    ):
        """A link placed in a symlinked directory must still reach its source."""
        source = tmp_path / "package" / "config" / "app.toml"
        source.parent.mkdir(parents=True)
        source.write_text("content")
        (tmp_path / real_dir).mkdir(parents=True)
        (tmp_path / "target").mkdir()
        (tmp_path / "target" / "config").symlink_to(tmp_path / real_dir)
        link = tmp_path / "target" / "config" / "app.toml"

        link.symlink_to(Symlink(link, source).relative_source_path)

        assert link.read_text() == "content"

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


class TestObserve:
    """Tests for observe(), the single classifier of what is at a link path."""

    @pytest.mark.parametrize("state", LinkState)
    def test_recognises_every_state(self, nested, occupy, state):
        occupy(nested, state)

        assert observe(nested) is state

    def test_link_to_missing_source_is_still_correct(self, nested, occupy):
        """A link is judged by where it points, so uninstall works after
        the package has been deleted."""
        occupy(nested, LinkState.CORRECT)
        nested.source_path.unlink()

        assert observe(nested) is LinkState.CORRECT

    def test_relative_link_to_source_is_correct(self, nested):
        nested.link_path.parent.mkdir()
        nested.link_path.symlink_to(nested.relative_source_path)

        assert observe(nested) is LinkState.CORRECT

    @pytest.mark.parametrize("state", LinkState)
    def test_does_not_change_the_filesystem(
        self, nested, occupy, snapshot, tmp_path, state
    ):
        occupy(nested, state)
        before = snapshot(tmp_path)

        observe(nested)

        assert snapshot(tmp_path) == before


class TestEnsureUnchanged:
    """Tests for ensure_unchanged()."""

    def test_passes_when_every_state_matches(self, nested, occupy):
        occupy(nested, LinkState.FILE)

        ensure_unchanged([(nested, LinkState.FILE)])

    def test_raises_naming_the_paths_that_changed(self, nested, occupy):
        occupy(nested, LinkState.FILE)

        with pytest.raises(StalePlanError) as excinfo:
            ensure_unchanged([(nested, LinkState.ABSENT)])

        assert excinfo.value.paths == [nested.link_path]


class TestCreateSymlink:
    """Tests for create_symlink()."""

    def test_creates_link_and_parent_directories(self, nested):
        create_symlink(nested)

        assert observe(nested) is LinkState.CORRECT
        assert nested.link_path.read_text() == "app contents"

    def test_link_is_relative(self, nested):
        """Relative links survive the home directory being moved or remounted."""
        create_symlink(nested)

        assert not nested.link_path.readlink().is_absolute()

    def test_refuses_to_overwrite(self, nested, occupy):
        occupy(nested, LinkState.FILE)

        with pytest.raises(FileExistsError):
            create_symlink(nested)

        assert nested.link_path.read_text() == "user data"
