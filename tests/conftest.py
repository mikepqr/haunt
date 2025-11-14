"""Global pytest configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def isolated_registry(tmp_path, monkeypatch):
    """Automatically redirect Registry.default_path to tmp_path for all tests.

    This ensures tests don't interfere with the user's real registry.
    Tests that need to override this behavior can monkeypatch again.
    """
    registry_path = tmp_path / "registry.json"
    monkeypatch.setattr(
        "haunt._registry.Registry.default_path", lambda cls: registry_path
    )
