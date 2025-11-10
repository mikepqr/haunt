"""Tests for high-level operations."""

from pathlib import Path
from unittest.mock import patch

import pytest

from haunt.exceptions import ConflictError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.models import ConflictMode
from haunt.models import CorrectSymlinkConflict
from haunt.models import DifferentSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import FileConflict
from haunt.models import InstallPlan
from haunt.models import Symlink
from haunt.operations import compute_install_plan
from haunt.operations import execute_install_plan
from haunt.registry import Registry


class TestComputeInstallPlan:
    """Tests for compute_install_plan()."""

    def test_calls_normalize_package_dir(self, tmp_path):
        """Test that compute_install_plan calls normalize_package_dir."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").write_text("content")
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        with patch(
            "haunt.operations.install.normalize_package_dir", return_value=package_dir
        ) as mock_normalize:
            compute_install_plan(package_dir, target_dir)
            mock_normalize.assert_called_once()

    def test_calls_normalize_target_dir(self, tmp_path):
        """Test that compute_install_plan calls normalize_target_dir."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").write_text("content")
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        with patch(
            "haunt.operations.install.normalize_target_dir", return_value=target_dir
        ) as mock_normalize:
            compute_install_plan(package_dir, target_dir)
            mock_normalize.assert_called_once()

    def test_simple_install_with_no_conflicts(self, tmp_path):
        """Test planning install with no existing files."""
        # Create package with some files
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file1.txt").write_text("content1")
        (package_dir / "file2.txt").write_text("content2")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        plan = compute_install_plan(package_dir, target_dir)

        assert plan.package_name == package_dir.name
        assert plan.package_dir == package_dir
        assert plan.target_dir == target_dir
        assert len(plan.symlinks_to_create) == 2
        assert len(plan.conflicts) == 0

        # Check symlinks
        link_paths = {s.link_path for s in plan.symlinks_to_create}
        assert target_dir / "file1.txt" in link_paths
        assert target_dir / "file2.txt" in link_paths

    def test_install_with_nested_files(self, tmp_path):
        """Test planning install with nested directory structure."""
        package_dir = tmp_path / "package"
        (package_dir / "config" / "nvim").mkdir(parents=True)
        (package_dir / "config" / "nvim" / "init.vim").write_text("content")
        (package_dir / "bashrc").write_text("content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        plan = compute_install_plan(package_dir, target_dir)

        assert len(plan.symlinks_to_create) == 2
        link_paths = {s.link_path for s in plan.symlinks_to_create}
        assert target_dir / "config" / "nvim" / "init.vim" in link_paths
        assert target_dir / "bashrc" in link_paths
        assert len(plan.conflicts) == 0

    def test_detects_file_conflict(self, tmp_path):
        """Test that existing regular files are detected as conflicts."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "bashrc").write_text("new content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "bashrc").write_text("old content")

        plan = compute_install_plan(package_dir, target_dir)

        assert len(plan.symlinks_to_create) == 0
        assert len(plan.conflicts) == 1
        conflict = plan.conflicts[0]
        assert conflict.path == target_dir / "bashrc"
        assert isinstance(conflict, FileConflict)

    def test_detects_wrong_symlink_conflict(self, tmp_path):
        """Test that symlinks pointing to wrong location are conflicts."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "bashrc").write_text("content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        wrong_source = tmp_path / "wrong.txt"
        wrong_source.write_text("wrong")
        (target_dir / "bashrc").symlink_to(wrong_source)

        plan = compute_install_plan(package_dir, target_dir)

        assert len(plan.symlinks_to_create) == 0
        assert len(plan.conflicts) == 1
        conflict = plan.conflicts[0]
        assert conflict.path == target_dir / "bashrc"
        assert isinstance(conflict, DifferentSymlinkConflict)
        assert conflict.points_to == wrong_source

    def test_no_conflict_when_symlink_already_correct(self, tmp_path):
        """Test that correctly pointing symlinks are reported as CORRECT_SYMLINK."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "bashrc").write_text("content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlink that already points correctly (relative)
        # target/bashrc -> ../package/bashrc
        target_link = target_dir / "bashrc"
        target_link.symlink_to(Path("../package/bashrc"))

        plan = compute_install_plan(package_dir, target_dir)

        # Should have one CORRECT_SYMLINK conflict (for reporting) and no files to link
        assert len(plan.conflicts) == 1
        assert isinstance(plan.conflicts[0], CorrectSymlinkConflict)
        assert len(plan.symlinks_to_create) == 0

    def test_symlinks_use_absolute_paths(self, tmp_path):
        """Test that symlinks in plan use absolute paths."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "bashrc").write_text("content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        plan = compute_install_plan(package_dir, target_dir)

        assert len(plan.symlinks_to_create) == 1
        symlink = plan.symlinks_to_create[0]
        assert symlink.link_path == target_dir / "bashrc"
        # Source should be absolute
        assert symlink.source_path == package_dir / "bashrc"
        # But relative_source_path should give relative version
        assert symlink.relative_source_path == Path("../package/bashrc")

    def test_abort_mode_keeps_conflicts_in_conflict_list(self, tmp_path):
        """Test that ABORT mode keeps conflicts in conflicts list only."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file1.txt").write_text("new")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file1.txt").write_text("existing")

        plan = compute_install_plan(
            package_dir, target_dir, on_conflict=ConflictMode.ABORT
        )

        # File conflict should be in conflicts, not symlinks_to_create
        assert len(plan.conflicts) == 1
        assert isinstance(plan.conflicts[0], FileConflict)
        assert len(plan.symlinks_to_create) == 0

    def test_force_mode_moves_file_conflicts_to_create_list(self, tmp_path):
        """Test that FORCE mode includes file conflicts in symlinks_to_create."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file1.txt").write_text("new")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file1.txt").write_text("existing")

        plan = compute_install_plan(
            package_dir, target_dir, on_conflict=ConflictMode.FORCE
        )

        # Conflict should be in both lists for tracking
        assert len(plan.conflicts) == 1
        assert isinstance(plan.conflicts[0], FileConflict)
        # And in symlinks_to_create for execution
        assert len(plan.symlinks_to_create) == 1
        assert plan.symlinks_to_create[0].link_path == target_dir / "file1.txt"

    def test_force_mode_does_not_include_directory_conflicts(self, tmp_path):
        """Test that FORCE mode does NOT include directory conflicts in symlinks_to_create."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file1.txt").write_text("new")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file1.txt").mkdir()

        plan = compute_install_plan(
            package_dir, target_dir, on_conflict=ConflictMode.FORCE
        )

        # Directory conflict should be in conflicts
        assert len(plan.conflicts) == 1
        assert isinstance(plan.conflicts[0], DirectoryConflict)
        # But NOT in symlinks_to_create
        assert len(plan.symlinks_to_create) == 0

    def test_skip_mode_keeps_conflicts_in_conflict_list(self, tmp_path):
        """Test that SKIP mode keeps conflicts in conflicts list only."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file1.txt").write_text("new")
        (package_dir / "file2.txt").write_text("new2")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "file1.txt").write_text("existing")

        plan = compute_install_plan(
            package_dir, target_dir, on_conflict=ConflictMode.SKIP
        )

        # Conflict should be in conflicts, not symlinks_to_create
        assert len(plan.conflicts) == 1
        assert isinstance(plan.conflicts[0], FileConflict)
        # But file2 should be in symlinks_to_create
        assert len(plan.symlinks_to_create) == 1
        assert plan.symlinks_to_create[0].link_path == target_dir / "file2.txt"


class TestExecuteInstallPlan:
    """Tests for execute_install_plan()."""

    def test_creates_symlinks_from_plan(self, tmp_path):
        """Test that symlinks in plan are created."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        # Create a plan with symlinks to create
        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=package_dir / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=package_dir / "file2.txt",
                ),
            ],
            conflicts=[],
        )

        execute_install_plan(plan, registry_path)

        # Check symlinks were created
        assert (target_dir / "file1.txt").is_symlink()
        assert (target_dir / "file2.txt").is_symlink()
        assert (target_dir / "file1.txt").readlink() == Path("../package/file1.txt")
        assert (target_dir / "file2.txt").readlink() == Path("../package/file2.txt")

    def test_updates_registry(self, tmp_path):
        """Test that registry is updated with package info."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[
                Symlink(
                    link_path=target_dir / "bashrc",
                    source_path=package_dir / "bashrc",
                ),
            ],
            conflicts=[],
        )

        execute_install_plan(plan, registry_path)

        # Check registry was updated
        registry = Registry.load(registry_path)
        assert "test-package" in registry.packages
        entry = registry.packages["test-package"]
        assert entry.name == "test-package"
        assert entry.target_dir == target_dir
        assert len(entry.symlinks) == 1
        assert entry.symlinks[0].link_path == target_dir / "bashrc"
        assert entry.symlinks[0].source_path == package_dir / "bashrc"

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created for nested symlinks."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[
                Symlink(
                    link_path=target_dir / "config" / "nvim" / "init.vim",
                    source_path=package_dir / "config/nvim/init.vim",
                ),
            ],
            conflicts=[],
        )

        execute_install_plan(plan, registry_path)

        # Check parent directories were created
        link = target_dir / "config" / "nvim" / "init.vim"
        assert link.parent.exists()
        assert link.is_symlink()

    def test_handles_empty_plan(self, tmp_path):
        """Test that empty plan doesn't create anything."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[],
        )

        execute_install_plan(plan, registry_path)

        # Registry should still be updated
        registry = Registry.load(registry_path)
        assert "test-package" in registry.packages
        assert registry.packages["test-package"].symlinks == []

    def test_includes_already_correct_symlinks_in_registry(self, tmp_path):
        """Test that already-correct symlinks are added to registry for uninstall."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        # Create plan with one new symlink and one already-correct
        new_symlink = Symlink(
            link_path=target_dir / "file1.txt",
            source_path=package_dir / "file1.txt",
        )

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[new_symlink],
            conflicts=[
                CorrectSymlinkConflict(
                    path=target_dir / "file2.txt",
                    points_to=Path(
                        "../package/file2.txt"
                    ),  # Relative path from readlink
                )
            ],
        )

        execute_install_plan(plan, registry_path)

        # Check registry includes both symlinks
        registry = Registry.load(registry_path)
        entry = registry.packages["test-package"]
        assert len(entry.symlinks) == 2

        # Check we have both symlinks with absolute paths
        link_paths = {s.link_path for s in entry.symlinks}
        assert target_dir / "file1.txt" in link_paths
        assert target_dir / "file2.txt" in link_paths

        source_paths = {s.source_path for s in entry.symlinks}
        assert package_dir / "file1.txt" in source_paths
        assert package_dir / "file2.txt" in source_paths

    def test_raises_for_directory_conflicts_in_abort_mode(self, tmp_path):
        """Test that directory conflicts raise ConflictError in ABORT mode."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[
                DirectoryConflict(
                    path=target_dir / "somedir",
                )
            ],
        )

        with pytest.raises(ConflictError) as exc_info:
            execute_install_plan(plan, registry_path, on_conflict=ConflictMode.ABORT)

        assert len(exc_info.value.conflicts) == 1
        assert isinstance(exc_info.value.conflicts[0], DirectoryConflict)

    def test_raises_for_directory_conflicts_even_in_force_mode(self, tmp_path):
        """Test that directory conflicts raise ConflictError even in FORCE mode."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[
                DirectoryConflict(
                    path=target_dir / "somedir",
                )
            ],
        )

        with pytest.raises(ConflictError) as exc_info:
            execute_install_plan(plan, registry_path, on_conflict=ConflictMode.FORCE)

        assert len(exc_info.value.conflicts) == 1
        assert isinstance(exc_info.value.conflicts[0], DirectoryConflict)

    def test_raises_for_file_conflicts_in_abort_mode(self, tmp_path):
        """Test that file conflicts raise ConflictError in ABORT mode."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[
                FileConflict(
                    path=target_dir / "file.txt",
                )
            ],
        )

        with pytest.raises(ConflictError) as exc_info:
            execute_install_plan(plan, registry_path, on_conflict=ConflictMode.ABORT)

        assert len(exc_info.value.conflicts) == 1
        assert isinstance(exc_info.value.conflicts[0], FileConflict)

    def test_succeeds_with_file_conflicts_in_skip_mode(self, tmp_path):
        """Test that file conflicts don't raise in SKIP mode."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        plan = InstallPlan(
            package_name="test-package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[
                FileConflict(
                    path=target_dir / "file.txt",
                )
            ],
        )

        # Should not raise
        execute_install_plan(plan, registry_path, on_conflict=ConflictMode.SKIP)

        # Registry should still be updated
        registry = Registry.load(registry_path)
        assert "test-package" in registry.packages

    def test_raises_for_package_name_collision(self, tmp_path):
        """Test that installing a package with the same name from different path raises error."""
        # Two different package directories with the same basename
        package_dir1 = tmp_path / "dotfiles1" / "shell"
        package_dir2 = tmp_path / "dotfiles2" / "shell"
        target_dir = tmp_path / "target"
        registry_path = tmp_path / "registry.json"

        # Install first package
        plan1 = InstallPlan(
            package_name="shell",
            package_dir=package_dir1,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[],
        )
        execute_install_plan(plan1, registry_path)

        # Try to install second package with same name but different path
        plan2 = InstallPlan(
            package_name="shell",
            package_dir=package_dir2,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[],
        )

        with pytest.raises(PackageAlreadyInstalledError) as exc_info:
            execute_install_plan(plan2, registry_path)

        # Check error details
        error = exc_info.value
        assert error.package_name == "shell"
        assert error.existing_path == str(package_dir1)
        assert error.new_path == str(package_dir2)

    def test_allows_reinstall_from_same_path(self, tmp_path):
        """Test that reinstalling a package from the same path is allowed (idempotent)."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"
        registry_path = tmp_path / "registry.json"

        # Install package
        plan1 = InstallPlan(
            package_name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[],
        )
        execute_install_plan(plan1, registry_path)

        # Reinstall from same path - should not raise
        plan2 = InstallPlan(
            package_name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks_to_create=[],
            conflicts=[],
        )
        execute_install_plan(plan2, registry_path)  # Should not raise

        # Registry should still have the package
        registry = Registry.load(registry_path)
        assert "package" in registry.packages
        assert registry.packages["package"].package_dir == package_dir
