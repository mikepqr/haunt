"""Basic tests for haunt CLI."""

from haunt.cli import main


def test_main():
    """Test that main() runs without error."""
    result = main()
    assert result == 0
