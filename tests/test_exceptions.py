"""Tests for haunt exceptions."""

from pathlib import Path

from haunt.exceptions import ConflictError
from haunt.models import ConflictInfo
from haunt.models import ConflictType


class TestConflictError:
    """Tests for ConflictError."""

    def test_formats_message_with_few_conflicts(self):
        """Test that error message lists all conflicts when 3 or fewer."""
        conflicts = [
            ConflictInfo(
                path=Path("/home/user/.bashrc"),
                type=ConflictType.FILE,
                points_to=None,
            ),
            ConflictInfo(
                path=Path("/home/user/.vimrc"),
                type=ConflictType.FILE,
                points_to=None,
            ),
        ]

        error = ConflictError(conflicts)

        assert ".bashrc" in str(error)
        assert ".vimrc" in str(error)
        assert "..." not in str(error)

    def test_formats_message_with_many_conflicts(self):
        """Test that error message truncates and shows count when > 3 conflicts."""
        conflicts = [
            ConflictInfo(
                path=Path(f"/home/user/.file{i}"),
                type=ConflictType.FILE,
                points_to=None,
            )
            for i in range(5)
        ]

        error = ConflictError(conflicts)

        # Should show first 3 and a total count
        assert "..." in str(error)
        assert "(5 total)" in str(error)
