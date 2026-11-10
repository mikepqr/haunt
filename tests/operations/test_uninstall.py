"""Tests for plan_uninstall() and apply_uninstall()."""

import shutil

import pytest

from haunt import apply_install
from haunt import apply_uninstall
from haunt import plan_install
from haunt import plan_uninstall
from haunt._registry import Registry
from haunt.exceptions import PackageNotFoundError
from haunt.exceptions import StalePlanError
from haunt.models import LinkState


@pytest.fixture
def installed(package, target):
    """The package, installed into a target that also holds the user's own files."""
    (target / "config").mkdir()
    (target / "config" / "mine.toml").write_text("user data")
    (target / "notes").write_text("user data")
    apply_install(plan_install(package, target))


def uninstall(package_name="package"):
    plan = plan_uninstall(package_name)
    apply_uninstall(plan)
    return plan


def test_uninstall_undoes_install(package, target, snapshot):
    before = snapshot(target)
    apply_install(plan_install(package, target))

    uninstall()

    assert snapshot(target) == before
    assert Registry().packages == {}


@pytest.mark.usefixtures("installed")
def test_uninstall_leaves_the_users_own_files(target, snapshot):
    uninstall()

    assert snapshot(target) == {
        "config": "directory",
        "config/mine.toml": "file: user data",
        "notes": "file: user data",
    }


@pytest.mark.usefixtures("installed")
def test_planning_changes_nothing(tmp_path, snapshot):
    before = snapshot(tmp_path)

    plan_uninstall("package")

    assert snapshot(tmp_path) == before


@pytest.mark.usefixtures("installed")
def test_uninstall_works_after_the_package_is_deleted(package, target):
    shutil.rmtree(package)

    uninstall()

    assert not (target / "bashrc").is_symlink()
    assert not (target / "config" / "app.toml").is_symlink()


def test_unknown_package_raises():
    with pytest.raises(PackageNotFoundError):
        plan_uninstall("nonexistent")


@pytest.mark.parametrize("state", [s for s in LinkState if s is not LinkState.CORRECT])
def test_only_removes_links_that_are_still_as_installed(
    package, target, nested, occupy, snapshot, state
):
    """Whatever has since happened to a link path, uninstall leaves it alone,
    still removes the package's other links, and forgets the package."""
    apply_install(plan_install(package, target))
    occupy(nested, state)
    target_before, package_before = snapshot(target), snapshot(package)

    plan = uninstall()

    missing = state in (LinkState.ABSENT, LinkState.PARENT_NOT_DIRECTORY)
    assert [s.link_path for s in plan.symlinks_to_remove] == [target / "bashrc"]
    assert plan.missing_symlinks == ([nested.link_path] if missing else [])
    assert plan.modified_symlinks == ([] if missing else [nested])
    del target_before["bashrc"]
    assert snapshot(target) == target_before
    assert snapshot(package) == package_before
    assert Registry().packages == {}


@pytest.mark.usefixtures("installed")
def test_refuses_when_a_link_has_changed_since_planning(
    target, nested, occupy, snapshot
):
    plan = plan_uninstall("package")
    occupy(nested, LinkState.FILE)
    before = snapshot(target)

    with pytest.raises(StalePlanError) as excinfo:
        apply_uninstall(plan)

    assert excinfo.value.paths == [nested.link_path]
    assert snapshot(target) == before
    assert "package" in Registry().packages
