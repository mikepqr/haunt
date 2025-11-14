"""Unit tests for find_unwanted_symlinks()."""

from datetime import datetime

from haunt._registry import Registry
from haunt.models import PackageEntry
from haunt.models import Symlink
from haunt.operations.install import find_unwanted_symlinks


class TestFindUnwantedSymlinks:
    """Tests for find_unwanted_symlinks()."""

    def test_returns_empty_when_package_not_in_registry(self, tmp_path, monkeypatch):
        """Test that no unwanted symlinks when package not in registry."""
        package_dir = tmp_path / "package"
        target_dir = tmp_path / "target"

        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        assert result == []

    def test_returns_empty_when_no_unwanted(self, tmp_path, monkeypatch):
        """Test no unwanted symlinks when all old symlinks are still wanted."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create actual symlinks
        (package_dir / "file1.txt").write_text("content1")
        (package_dir / "file2.txt").write_text("content2")
        (target_dir / "file1.txt").symlink_to(package_dir / "file1.txt")
        (target_dir / "file2.txt").symlink_to(package_dir / "file2.txt")

        # Set up registry with existing install
        existing_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
            Symlink(
                link_path=target_dir / "file2.txt",
                source_path=package_dir / "file2.txt",
            ),
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # Both symlinks are still wanted
        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
            Symlink(
                link_path=target_dir / "file2.txt",
                source_path=package_dir / "file2.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        assert result == []

    def test_finds_unwanted_symlink_when_file_removed(self, tmp_path, monkeypatch):
        """Test that unwanted symlink is found when file removed from package."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create actual symlinks
        (package_dir / "file1.txt").write_text("content1")
        (target_dir / "file1.txt").symlink_to(package_dir / "file1.txt")

        # Set up registry with existing install (had file1 and file2)
        existing_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
            Symlink(
                link_path=target_dir / "file2.txt",
                source_path=package_dir / "file2.txt",
            ),
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # Only file2 is wanted now (file1 was removed)
        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file2.txt",
                source_path=package_dir / "file2.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        assert len(result) == 1
        assert result[0].link_path == target_dir / "file1.txt"

    def test_does_not_include_modified_symlinks(self, tmp_path, monkeypatch):
        """Test that modified symlinks are not returned as unwanted."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlink pointing to wrong location (user modified)
        other_file = tmp_path / "other.txt"
        other_file.write_text("other")
        (target_dir / "file1.txt").symlink_to(other_file)

        # Set up registry with existing install
        existing_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # file1 is not wanted anymore
        wanted_symlinks = []

        result = find_unwanted_symlinks("package", wanted_symlinks)

        # Modified symlink should not be in result (user protection)
        assert result == []

    def test_wanted_symlinks_not_considered_unwanted(self, tmp_path, monkeypatch):
        """Test that symlinks in wanted set aren't considered unwanted."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlink that already points correctly
        (package_dir / "file1.txt").write_text("content1")
        (target_dir / "file1.txt").symlink_to(package_dir / "file1.txt")

        # Set up registry with existing install
        existing_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # file1 is still wanted
        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=package_dir / "file1.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        # file1 should not be unwanted (it's still wanted)
        assert result == []

    def test_handles_multiple_unwanted(self, tmp_path, monkeypatch):
        """Test finding multiple unwanted symlinks at once."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create actual symlinks
        for name in ["file1.txt", "file2.txt", "file3.txt"]:
            (package_dir / name).write_text("content")
            (target_dir / name).symlink_to(package_dir / name)

        # Set up registry with existing install
        existing_symlinks = [
            Symlink(
                link_path=target_dir / f"file{i}.txt",
                source_path=package_dir / f"file{i}.txt",
            )
            for i in range(1, 4)
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # Only file2 is wanted
        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file2.txt",
                source_path=package_dir / "file2.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        # Should find file1 and file3 as unwanted
        assert len(result) == 2
        unwanted_paths = {s.link_path for s in result}
        assert target_dir / "file1.txt" in unwanted_paths
        assert target_dir / "file3.txt" in unwanted_paths
        assert target_dir / "file2.txt" not in unwanted_paths

    def test_detects_unwanted_when_source_changes(self, tmp_path, monkeypatch):
        """Test that symlink is unwanted when source path changes."""
        old_package_dir = tmp_path / "old_package"
        old_package_dir.mkdir()
        new_package_dir = tmp_path / "new_package"
        new_package_dir.mkdir()
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Create symlink pointing to old location
        (old_package_dir / "file1.txt").write_text("old content")
        (target_dir / "file1.txt").symlink_to(old_package_dir / "file1.txt")

        # Set up registry with existing install pointing to old package
        existing_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=old_package_dir / "file1.txt",
            ),
        ]

        registry = Registry()
        registry.packages["package"] = PackageEntry(
            name="package",
            package_dir=old_package_dir,
            target_dir=target_dir,
            symlinks=existing_symlinks,
            installed_at=datetime.now().astimezone().isoformat(),
        )
        registry.save()

        # wanted symlinks point to new package (same link path, different source)
        wanted_symlinks = [
            Symlink(
                link_path=target_dir / "file1.txt",
                source_path=new_package_dir / "file1.txt",
            ),
        ]

        result = find_unwanted_symlinks("package", wanted_symlinks)

        # Old symlink should be unwanted even though path is wanted
        assert len(result) == 1
        assert result[0].link_path == target_dir / "file1.txt"
        assert result[0].source_path == old_package_dir / "file1.txt"
