"""Tests for file discovery operations."""

from pathlib import Path


from haunt.files import discover_files


class TestDiscoverFiles:
    """Tests for discover_files()."""

    def test_discover_files_in_empty_directory(self, tmp_path):
        """Test discovering files in an empty directory."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        files = discover_files(package_dir)

        assert files == []

    def test_discover_single_file(self, tmp_path):
        """Test discovering a single file in package root."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".bashrc").touch()

        files = discover_files(package_dir)

        assert files == [Path(".bashrc")]

    def test_discover_multiple_files_in_root(self, tmp_path):
        """Test discovering multiple files in package root."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".bashrc").touch()
        (package_dir / ".vimrc").touch()
        (package_dir / ".profile").touch()

        files = discover_files(package_dir)

        assert len(files) == 3
        assert Path(".bashrc") in files
        assert Path(".vimrc") in files
        assert Path(".profile") in files

    def test_discover_files_in_subdirectories(self, tmp_path):
        """Test discovering files in nested subdirectories."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".bashrc").touch()

        config_dir = package_dir / ".config"
        config_dir.mkdir()
        (config_dir / "settings.json").touch()

        nvim_dir = config_dir / "nvim"
        nvim_dir.mkdir()
        (nvim_dir / "init.vim").touch()

        files = discover_files(package_dir)

        assert len(files) == 3
        assert Path(".bashrc") in files
        assert Path(".config/settings.json") in files
        assert Path(".config/nvim/init.vim") in files

    def test_discover_files_ignores_directories(self, tmp_path):
        """Test that directories themselves are not included in file list."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").touch()

        subdir = package_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").touch()

        files = discover_files(package_dir)

        assert len(files) == 2
        assert Path("file.txt") in files
        assert Path("subdir/nested.txt") in files
        # "subdir" itself should NOT be in the list
        assert Path("subdir") not in files

    def test_discover_files_returns_sorted_list(self, tmp_path):
        """Test that files are returned in sorted order."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "zebra").touch()
        (package_dir / "apple").touch()
        (package_dir / "middle").touch()

        files = discover_files(package_dir)

        assert files == sorted(files)

    def test_discover_files_uses_relative_paths(self, tmp_path):
        """Test that returned paths are relative to package_dir."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").touch()

        files = discover_files(package_dir)

        # Should be relative, not absolute
        assert files[0] == Path("file.txt")
        assert not files[0].is_absolute()

    def test_discover_files_with_hidden_files(self, tmp_path):
        """Test that hidden files (starting with .) are discovered."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".hidden").touch()
        (package_dir / "visible").touch()

        files = discover_files(package_dir)

        assert Path(".hidden") in files
        assert Path("visible") in files

    def test_discover_files_includes_symlinks(self, tmp_path):
        """Test that symlinked files are discovered."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Create a file outside package
        external_file = tmp_path / "external.txt"
        external_file.touch()

        # Create symlink to it inside package
        link = package_dir / "link.txt"
        link.symlink_to(external_file)

        files = discover_files(package_dir)

        assert Path("link.txt") in files
