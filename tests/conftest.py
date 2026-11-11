"""Global pytest configuration and fixtures."""

from pathlib import Path

import pytest

from haunt.models import LinkState
from haunt.models import Symlink


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


@pytest.fixture
def package(tmp_path):
    """A package with one top-level file and one nested file."""
    package_dir = tmp_path / "package"
    (package_dir / "config").mkdir(parents=True)
    (package_dir / "bashrc").write_text("bashrc contents")
    (package_dir / "config" / "app.toml").write_text("app contents")
    return package_dir


@pytest.fixture
def target(tmp_path):
    """An empty target directory."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    return target_dir


@pytest.fixture
def nested(package, target):
    """The symlink wanted for the package's nested file."""
    return Symlink(
        link_path=target / "config" / "app.toml",
        source_path=package / "config" / "app.toml",
    )


def _occupy(symlink: Symlink, state: LinkState) -> None:
    """Arrange the filesystem so that symlink.link_path is in the given state.

    link_path's directory must be empty or absent, apart from link_path itself.
    """
    link, source = symlink.link_path, symlink.source_path
    if link.exists(follow_symlinks=False):
        link.unlink()
    if state in (LinkState.IS_SOURCE, LinkState.PARENT_NOT_DIRECTORY):
        if link.parent.exists():
            link.parent.rmdir()
    else:
        link.parent.mkdir(parents=True, exist_ok=True)

    match state:
        case LinkState.ABSENT:
            pass
        case LinkState.CORRECT:
            link.symlink_to(source)
        case LinkState.FOREIGN_LINK:
            link.symlink_to(link.parent)
        case LinkState.BROKEN_LINK:
            link.symlink_to("does-not-exist")
        case LinkState.FILE:
            link.write_text("user data")
        case LinkState.DIRECTORY:
            link.mkdir()
        case LinkState.IS_SOURCE:
            link.parent.symlink_to(source.parent)
        case LinkState.PARENT_NOT_DIRECTORY:
            link.parent.write_text("user data")


@pytest.fixture
def occupy():
    """Function that puts a symlink's link_path into a given LinkState."""
    return _occupy


def _snapshot(root: Path) -> dict[str, str]:
    """Describe every path under root, without following symlinks."""
    described = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            described[str(path.relative_to(root))] = f"link to {path.readlink()}"
        elif path.is_dir():
            described[str(path.relative_to(root))] = "directory"
        else:
            described[str(path.relative_to(root))] = f"file: {path.read_text()}"
    return described


@pytest.fixture
def snapshot():
    """Function that describes a directory tree, for before/after comparison."""
    return _snapshot
