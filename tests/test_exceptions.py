"""Tests for haunt exceptions."""

from pathlib import Path

from haunt.exceptions import ConflictError
from haunt.exceptions import StalePlanError
from haunt.models import Action
from haunt.models import LinkState
from haunt.models import PlannedLink
from haunt.models import Symlink


def _blocked(path: str) -> PlannedLink:
    symlink = Symlink(link_path=Path(path), source_path=Path("/package/file"))
    return PlannedLink(symlink, LinkState.FILE, Action.BLOCK)


class TestConflictError:
    """Tests for ConflictError."""

    def test_formats_message_with_few_conflicts(self):
        """Test that error message lists all conflicts when 3 or fewer."""
        error = ConflictError(
            [_blocked("/home/user/.bashrc"), _blocked("/home/user/.vimrc")]
        )

        assert ".bashrc" in str(error)
        assert ".vimrc" in str(error)
        assert "..." not in str(error)

    def test_formats_message_with_many_conflicts(self):
        """Test that error message truncates and shows count when > 3 conflicts."""
        error = ConflictError([_blocked(f"/home/user/.file{i}") for i in range(5)])

        # Should show first 3 and a total count
        assert "..." in str(error)
        assert "(5 total)" in str(error)


def test_stale_plan_error_names_the_changed_paths():
    error = StalePlanError([Path("/home/user/.bashrc")])

    assert "/home/user/.bashrc" in str(error)
