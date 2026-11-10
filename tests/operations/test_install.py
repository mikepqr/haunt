"""Tests for plan_install() and apply_install()."""

import shutil
from pathlib import Path

import pytest

from haunt import apply_install
from haunt import apply_uninstall
from haunt import plan_install
from haunt import plan_uninstall
from haunt._files.symlinks import create_symlink
from haunt._files.symlinks import observe
from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.exceptions import StalePlanError
from haunt.models import Action
from haunt.models import ConflictMode
from haunt.models import LinkState
from haunt.operations.install import decide


def install(package, target, on_conflict=ConflictMode.ABORT):
    plan = plan_install(package, target, on_conflict)
    apply_install(plan)
    return plan


def test_every_package_file_is_reachable_through_the_target(package, target):
    install(package, target)

    assert (target / "bashrc").is_symlink()
    assert (target / "bashrc").read_text() == "bashrc contents"
    assert (target / "config").is_dir() and not (target / "config").is_symlink()
    assert (target / "config" / "app.toml").is_symlink()
    assert (target / "config" / "app.toml").read_text() == "app contents"


def test_install_is_recorded_in_the_registry(package, target):
    plan = install(package, target)

    entry = Registry().packages["package"]
    assert entry.package_dir == package
    assert entry.target_dir == target
    assert entry.symlinks == [link.symlink for link in plan.links]


def test_planning_changes_nothing(package, target, snapshot, tmp_path):
    before = snapshot(tmp_path)

    plan_install(package, target)

    assert snapshot(tmp_path) == before


def test_installing_twice_is_a_no_op(package, target, snapshot):
    install(package, target)
    installed = snapshot(target)

    plan = install(package, target)

    assert {link.action for link in plan.links} == {Action.KEEP}
    assert plan.symlinks_to_remove == []
    assert snapshot(target) == installed


def test_relative_paths_are_resolved(package, target, monkeypatch):
    monkeypatch.chdir(package.parent)

    plan = plan_install(Path("package"), Path("target"))

    assert plan.package_dir == package
    assert plan.target_dir == target
    assert all(link.symlink.link_path.is_absolute() for link in plan.links)
    assert all(link.symlink.source_path.is_absolute() for link in plan.links)


@pytest.mark.parametrize("mode", ConflictMode)
@pytest.mark.parametrize("state", LinkState)
def test_install_onto_any_existing_state(
    package, target, nested, occupy, snapshot, state, mode
):
    """Whatever is found at a link path, in every conflict mode: install does
    what decide() says, touches nothing else, and never alters the package."""
    occupy(nested, state)
    target_before, package_before = snapshot(target), snapshot(package)
    action = decide(state, mode)

    if action is Action.BLOCK:
        with pytest.raises(ConflictError) as excinfo:
            install(package, target, mode)
        assert [c.symlink for c in excinfo.value.conflicts] == [nested]
        assert snapshot(target) == target_before
        assert Registry().packages == {}
    else:
        plan = install(package, target, mode)
        assert [link.action for link in plan.links if link.symlink == nested] == [
            action
        ]
        assert (target / "bashrc").read_text() == "bashrc contents"
        if action is Action.SKIP:
            target_after = snapshot(target)
            del target_after["bashrc"]
            assert target_after == target_before
        else:
            assert observe(nested) is LinkState.CORRECT
            assert nested.link_path.read_text() == "app contents"
    assert snapshot(package) == package_before


def test_package_in_a_stow_folded_directory_survives_force(package, target, nested):
    """Regression: with ~/config symlinked into the package, the "conflicting
    file" is the package file itself, and force used to replace it with a
    symlink to itself."""
    (target / "config").symlink_to(package / "config")

    with pytest.raises(ConflictError):
        install(package, target, ConflictMode.FORCE)

    assert not nested.source_path.is_symlink()
    assert nested.source_path.read_text() == "app contents"


class TestReinstall:
    """Reinstalling after the package's contents change."""

    def test_removes_links_for_files_no_longer_in_the_package(self, package, target):
        install(package, target)
        shutil.rmtree(package / "config")

        plan = install(package, target)

        assert [s.link_path for s in plan.symlinks_to_remove] == [
            target / "config" / "app.toml"
        ]
        assert not (target / "config").exists()
        assert [s.link_path for s in Registry().packages["package"].symlinks] == [
            target / "bashrc"
        ]

    def test_links_new_files(self, package, target):
        install(package, target)
        (package / "vimrc").write_text("vimrc contents")

        install(package, target)

        assert (target / "vimrc").read_text() == "vimrc contents"

    @pytest.mark.parametrize(
        "state", [s for s in LinkState if s is not LinkState.CORRECT]
    )
    def test_leaves_orphans_the_user_has_changed(
        self, package, target, nested, occupy, snapshot, state
    ):
        """An orphaned link is only removed if it is still exactly as haunt
        left it."""
        install(package, target)
        occupy(nested, state)
        nested.source_path.unlink(missing_ok=True)
        before = snapshot(target)

        plan = install(package, target)

        assert plan.symlinks_to_remove == []
        assert snapshot(target) == before


class TestStalePlan:
    """apply_install() refuses a plan the filesystem has moved on from."""

    def test_refuses_when_a_link_path_has_changed(
        self, package, target, nested, occupy, snapshot
    ):
        plan = plan_install(package, target)
        occupy(nested, LinkState.FILE)
        before = snapshot(target)

        with pytest.raises(StalePlanError) as excinfo:
            apply_install(plan)

        assert excinfo.value.paths == [nested.link_path]
        assert snapshot(target) == before
        assert Registry().packages == {}

    def test_refuses_when_an_orphan_has_changed(
        self, package, target, nested, occupy, snapshot
    ):
        install(package, target)
        nested.source_path.unlink()
        plan = plan_install(package, target)
        occupy(nested, LinkState.FILE)
        before = snapshot(target)

        with pytest.raises(StalePlanError):
            apply_install(plan)

        assert snapshot(target) == before


def fail_after(successes, function):
    """Wrap function so that it raises OSError once it has succeeded n times."""
    remaining = iter(range(successes))

    def wrapper(*args, **kwargs):
        if next(remaining, None) is None:
            raise OSError("simulated failure")
        return function(*args, **kwargs)

    return wrapper


class TestInterruptedInstall:
    """An install that fails part-way leaves nothing haunt doesn't know about."""

    @pytest.fixture
    def interrupted(self, package, target, monkeypatch):
        """Install the package, failing after the first link is created."""
        with monkeypatch.context() as patch:
            patch.setattr(
                "haunt.operations.install.create_symlink", fail_after(1, create_symlink)
            )
            with pytest.raises(OSError, match="simulated"):
                install(package, target)
        assert (target / "bashrc").is_symlink()

    @pytest.mark.usefixtures("interrupted")
    def test_can_be_uninstalled(self, target, snapshot):
        apply_uninstall(plan_uninstall("package"))

        assert snapshot(target) == {}

    @pytest.mark.usefixtures("interrupted")
    def test_can_be_completed_by_installing_again(self, package, target):
        plan = install(package, target)

        assert [link.action for link in plan.links] == [Action.KEEP, Action.CREATE]
        assert (target / "config" / "app.toml").read_text() == "app contents"

    def test_orphans_not_yet_removed_are_still_known(
        self, package, target, snapshot, monkeypatch
    ):
        install(package, target)
        (package / "bashrc").unlink()
        shutil.rmtree(package / "config")
        with monkeypatch.context() as patch:
            patch.setattr(Path, "unlink", fail_after(1, Path.unlink))
            with pytest.raises(OSError, match="simulated"):
                install(package, target)
        assert len([p for p in target.rglob("*") if p.is_symlink()]) == 1

        apply_uninstall(plan_uninstall("package"))

        assert snapshot(target) == {}


class TestPackageNameCollision:
    """Two package directories with the same basename cannot both be installed."""

    @pytest.fixture
    def namesake(self, tmp_path):
        other = tmp_path / "elsewhere" / "package"
        other.mkdir(parents=True)
        (other / "zshrc").write_text("zshrc contents")
        return other

    def test_plan_raises(self, package, target, namesake):
        install(package, target)

        with pytest.raises(PackageAlreadyInstalledError):
            plan_install(namesake, target)

    def test_apply_raises_if_the_namesake_was_installed_after_planning(
        self, package, target, namesake, snapshot
    ):
        plan = plan_install(namesake, target)
        install(package, target)
        before = snapshot(target)

        with pytest.raises(PackageAlreadyInstalledError):
            apply_install(plan)

        assert snapshot(target) == before
