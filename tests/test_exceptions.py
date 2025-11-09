"""Tests for haunt exceptions."""

from pathlib import Path

from haunt.exceptions import ConflictError
from haunt.models import FileConflict


class TestConflictError:
    """Tests for ConflictError."""

    def test_formats_message_with_few_conflicts(self):
        """Test that error message lists all conflicts when 3 or fewer."""
        conflicts = [
            FileConflict(path=Path("/home/user/.bashrc")),
            FileConflict(path=Path("/home/user/.vimrc")),
        ]

        error = ConflictError(conflicts)

        assert ".bashrc" in str(error)
        assert ".vimrc" in str(error)
        assert "..." not in str(error)

    def test_formats_message_with_many_conflicts(self):
        """Test that error message truncates and shows count when > 3 conflicts."""
        conflicts = [FileConflict(path=Path(f"/home/user/.file{i}")) for i in range(5)]

        error = ConflictError(conflicts)

        # Should show first 3 and a total count
        assert "..." in str(error)
        assert "(5 total)" in str(error)
