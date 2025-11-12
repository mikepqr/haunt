"""Tests for uninstall operations."""

from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from haunt._registry import Registry
from haunt.exceptions import PackageNotFoundError
from haunt.models import PackageEntry
from haunt.models import Symlink
from haunt.models import UninstallPlan
from haunt.operations import apply_uninstall
from haunt.operations import plan_uninstall


class TestPlanUninstall:
    """Tests for plan_uninstall()."""

    def test_simple_uninstall(self, tmp_path, monkeypatch):
        """Test planning uninstall for a simple package."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Create registry with package
        registry = Registry()
        registry.packages[package_dir.name] = PackageEntry(
            name=package_dir.name,
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=package_dir / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=package_dir / "file2.txt",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save()

        # Create the symlinks
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))
        (target_dir / "file2.txt").symlink_to(Path("../package/file2.txt"))

        plan = plan_uninstall(package_dir.name)

        assert plan.package_name == package_dir.name
        assert plan.target_dir == target_dir
        assert len(plan.symlinks_to_remove) == 2
        assert len(plan.missing_symlinks) == 0
        assert len(plan.modified_symlinks) == 0

        link_paths = {s.link_path for s in plan.symlinks_to_remove}
        assert target_dir / "file1.txt" in link_paths
        assert target_dir / "file2.txt" in link_paths

    def test_detects_missing_symlinks(self, tmp_path, monkeypatch):
        """Test that missing symlinks are reported."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Create registry with package
        registry = Registry()
        registry.packages[package_dir.name] = PackageEntry(
            name=package_dir.name,
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=package_dir / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=package_dir / "file2.txt",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save()

        # Only create one symlink
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))

        plan = plan_uninstall(package_dir.name)

        assert len(plan.symlinks_to_remove) == 1
        assert len(plan.missing_symlinks) == 1
        assert len(plan.modified_symlinks) == 0
        assert target_dir / "file2.txt" in plan.missing_symlinks

    def test_raises_for_unknown_package(self, tmp_path, monkeypatch):
        """Test that error is raised for unknown package."""
        package_dir = tmp_path / "nonexistent"
        package_dir.mkdir()
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Create empty registry
        registry = Registry()
        registry.save()

        with pytest.raises(PackageNotFoundError) as exc_info:
            plan_uninstall(package_dir.name)

        assert package_dir.name in str(exc_info.value)

    def test_computes_correct_source_paths(self, tmp_path, monkeypatch):
        """Test that symlinks have correct source paths for verification."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Create registry with package
        registry = Registry()
        registry.packages[package_dir.name] = PackageEntry(
            name=package_dir.name,
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "bashrc",
                    source_path=package_dir / "bashrc",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save()

        # Create symlink
        (target_dir / "bashrc").symlink_to(Path("../package/bashrc"))

        plan = plan_uninstall(package_dir.name)

        assert len(plan.symlinks_to_remove) == 1
        symlink = plan.symlinks_to_remove[0]
        assert symlink.link_path == target_dir / "bashrc"
        # Source should be absolute path
        assert symlink.source_path == package_dir / "bashrc"

    def test_detects_modified_symlinks(self, tmp_path, monkeypatch):
        """Test that symlinks pointing to wrong targets are detected as modified."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Create registry with package
        registry = Registry()
        registry.packages[package_dir.name] = PackageEntry(
            name=package_dir.name,
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=[
                Symlink(
                    link_path=target_dir / "file1.txt",
                    source_path=package_dir / "file1.txt",
                ),
                Symlink(
                    link_path=target_dir / "file2.txt",
                    source_path=package_dir / "file2.txt",
                ),
            ],
            installed_at="2025-01-01T00:00:00Z",
        )
        registry.save()

        # Create one correct symlink and one modified symlink
        (target_dir / "file1.txt").symlink_to(Path("../package/file1.txt"))
        # file2.txt points to wrong target (user modified it)
        (target_dir / "file2.txt").symlink_to(Path("../other/file2.txt"))

        plan = plan_uninstall(package_dir.name)

        # Should remove the correct symlink
        assert len(plan.symlinks_to_remove) == 1
        assert plan.symlinks_to_remove[0].link_path == target_dir / "file1.txt"

        # Should detect the modified symlink
        assert len(plan.modified_symlinks) == 1
        assert plan.modified_symlinks[0].link_path == target_dir / "file2.txt"

        # Should have no missing symlinks
        assert len(plan.missing_symlinks) == 0


class TestApplyUninstall:
    """Tests for apply_uninstall()."""

    def test_removes_symlinks_from_plan(self, tmp_path, monkeypatch):
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
            modified_symlinks=[],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )
        with patch("haunt.operations.uninstall.Registry", return_value=mock_registry):
            apply_uninstall(plan)

        # Check symlinks were removed
        assert not (target_dir / "file1.txt").exists()
        assert not (target_dir / "file2.txt").exists()

    def test_removes_empty_directories(self, tmp_path, monkeypatch):
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
            modified_symlinks=[],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )
        with patch("haunt.operations.uninstall.Registry", return_value=mock_registry):
            apply_uninstall(plan)

        # Check symlink and empty dirs were removed
        assert not (target_dir / "config" / "nvim" / "init.vim").exists()
        assert not (target_dir / "config" / "nvim").exists()
        assert not (target_dir / "config").exists()

    def test_updates_registry(self, tmp_path, monkeypatch):
        """Test that package is removed from registry."""
        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        with patch("haunt.operations.uninstall.Registry", return_value=mock_registry):
            # Create plan directly
            plan = UninstallPlan(
                package_name="test-package",
                target_dir=tmp_path / "target",
                symlinks_to_remove=[],
                missing_symlinks=[],
                modified_symlinks=[],
            )

            apply_uninstall(plan)

        # Check package was removed from registry
        assert "test-package" not in mock_registry.packages
        mock_registry.save.assert_called_once_with()

    def test_handles_missing_symlinks_in_plan(self, tmp_path, monkeypatch):
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
            modified_symlinks=[],
        )

        # Mock registry
        mock_registry = Mock(spec=Registry)
        mock_registry.packages = {"test-package": Mock()}

        registry_path = tmp_path / "registry.json"
        monkeypatch.setattr(
            "haunt._registry.Registry.default_path", lambda cls: registry_path
        )
        with patch("haunt.operations.uninstall.Registry", return_value=mock_registry):
            apply_uninstall(plan)

        # Should complete without error
        assert not (target_dir / "file1.txt").exists()
