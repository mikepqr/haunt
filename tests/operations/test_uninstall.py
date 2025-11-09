"""Tests for uninstall operations."""

from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from haunt.exceptions import PackageNotFoundError
from haunt.models import PackageEntry
from haunt.models import Symlink
from haunt.models import UninstallPlan
from haunt.operations import compute_uninstall_plan
from haunt.operations import execute_uninstall_plan
from haunt.registry import Registry


class TestComputeUninstallPlan:
    """Tests for compute_uninstall_plan()."""

    def test_simple_uninstall(self, tmp_path):
        """Test planning uninstall for a simple package."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        # Create registry with package
        registry = Registry()
        registry.packages["test-package"] = PackageEntry(
            name="test-package",
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=tmp_path / "package" / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=tmp_path / "package" / "file2.txt",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save(registry_path)

        # Create the symlinks
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))
        (target_dir / "file2.txt").symlink_to(Path("../package/file2.txt"))

        plan = compute_uninstall_plan("test-package", registry_path)

        assert plan.package_name == "test-package"
        assert plan.target_dir == target_dir
        assert len(plan.symlinks_to_remove) == 2
        assert len(plan.missing_symlinks) == 0

        link_paths = {s.link_path for s in plan.symlinks_to_remove}
        assert target_dir / "file1.txt" in link_paths
        assert target_dir / "file2.txt" in link_paths

    def test_detects_missing_symlinks(self, tmp_path):
        """Test that missing symlinks are reported."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        # Create registry with package
        registry = Registry()
        registry.packages["test-package"] = PackageEntry(
            name="test-package",
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=tmp_path / "package" / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=tmp_path / "package" / "file2.txt",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save(registry_path)

        # Only create one symlink
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))

        plan = compute_uninstall_plan("test-package", registry_path)

        assert len(plan.symlinks_to_remove) == 1
        assert len(plan.missing_symlinks) == 1
        assert target_dir / "file2.txt" in plan.missing_symlinks

    def test_raises_for_unknown_package(self, tmp_path):
        """Test that error is raised for unknown package."""
        registry_path = tmp_path / "registry.json"

        # Create empty registry
        registry = Registry()
        registry.save(registry_path)

        with pytest.raises(PackageNotFoundError) as exc_info:
            compute_uninstall_plan("nonexistent", registry_path)

        assert "nonexistent" in str(exc_info.value)

    def test_computes_correct_source_paths(self, tmp_path):
        """Test that symlinks have correct source paths for verification."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"

        # Create registry with package
        registry = Registry()
        registry.packages["test-package"] = PackageEntry(
            name="test-package",
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "bashrc",
                    source_path=tmp_path / "package" / "bashrc",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save(registry_path)

        # Create symlink
        (target_dir / "bashrc").symlink_to(Path("../package/bashrc"))

        plan = compute_uninstall_plan("test-package", registry_path)

        assert len(plan.symlinks_to_remove) == 1
        symlink = plan.symlinks_to_remove[0]
        assert symlink.link_path == target_dir / "bashrc"
        # Source should be absolute path
        assert symlink.source_path == tmp_path / "package" / "bashrc"


class TestExecuteUninstallPlan:
    """Tests for execute_uninstall_plan()."""

    def test_removes_symlinks_from_plan(self, tmp_path):
        """Test that symlinks in plan are removed."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlinks
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))
        (target_dir / "file2.txt").symlink_to(Path("../package/file2.txt"))

        # Create plan directly
        plan = UninstallPlan(
            package_name="test-package",
            target_dir=target_dir,
            symlinks_to_remove=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=tmp_path / "package" / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=tmp_path / "package" / "file2.txt",
                ),
            ],
            missing_symlinks=[],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        with patch(
            "haunt.operations.uninstall.Registry.load", return_value=mock_registry
        ):
            execute_uninstall_plan(plan, registry_path)

        # Check symlinks were removed
        assert not (target_dir / "file1.txt").exists()
        assert not (target_dir / "file2.txt").exists()

    def test_removes_empty_directories(self, tmp_path):
        """Test that empty directories are cleaned up."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create nested symlink
        (target_dir / "config" / "nvim").mkdir(parents=True)
        (target_dir / "config" / "nvim" / "init.vim").symlink_to(
            Path("../../../package/config/nvim/init.vim")
        )

        # Create plan directly
        plan = UninstallPlan(
            package_name="test-package",
            target_dir=target_dir,
            symlinks_to_remove=[
                Symlink(
                    link_path=target_dir / "config" / "nvim" / "init.vim",
                    source_path=tmp_path / "package" / "config/nvim/init.vim",
                ),
            ],
            missing_symlinks=[],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        with patch(
            "haunt.operations.uninstall.Registry.load", return_value=mock_registry
        ):
            execute_uninstall_plan(plan, registry_path)

        # Check symlink and empty dirs were removed
        assert not (target_dir / "config" / "nvim" / "init.vim").exists()
        assert not (target_dir / "config" / "nvim").exists()
        assert not (target_dir / "config").exists()

    def test_updates_registry(self, tmp_path):
        """Test that package is removed from registry."""
        registry_path = tmp_path / "registry.json"

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        with patch(
            "haunt.operations.uninstall.Registry.load", return_value=mock_registry
        ):
            # Create plan directly
            plan = UninstallPlan(
                package_name="test-package",
                target_dir=tmp_path / "target",
                symlinks_to_remove=[],
                missing_symlinks=[],
            )

            execute_uninstall_plan(plan, registry_path)

        # Check package was removed from registry
        assert "test-package" not in mock_registry.packages
        mock_registry.save.assert_called_once_with(registry_path)

    def test_handles_missing_symlinks_in_plan(self, tmp_path):
        """Test that plans with missing symlinks don't cause errors."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlink
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))

        # Create plan with missing symlinks reported
        plan = UninstallPlan(
            package_name="test-package",
            target_dir=target_dir,
            symlinks_to_remove=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=tmp_path / "package" / "file1.txt",
                ),
            ],
            missing_symlinks=["file2.txt"],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        with patch(
            "haunt.operations.uninstall.Registry.load", return_value=mock_registry
        ):
            execute_uninstall_plan(plan, registry_path)

        # Should complete without error
        assert not (target_dir / "file1.txt").exists()
