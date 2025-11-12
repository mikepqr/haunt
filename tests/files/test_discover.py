"""Tests for file discovery operations."""

import subprocess
from pathlib import Path
from unittest.mock import patch

from haunt._files.discover import _should_use_git
from haunt._files.discover import discover_files
from haunt._files.discover import discover_files_git
from haunt._files.discover import discover_files_walk


class TestDiscoverFilesWalk:
    """Tests for discover_files_walk()."""

    def test_discover_files_walk_in_empty_directory(self, tmp_path):
        """Test discovering files in an empty directory."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        files = discover_files_walk(package_dir)

        assert files == []

    def test_discover_single_file(self, tmp_path):
        """Test discovering a single file in package root."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".bashrc").touch()

        files = discover_files_walk(package_dir)

        assert files == [Path(".bashrc")]

    def test_discover_multiple_files_in_root(self, tmp_path):
        """Test discovering multiple files in package root."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".bashrc").touch()
        (package_dir / ".vimrc").touch()
        (package_dir / ".profile").touch()

        files = discover_files_walk(package_dir)

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

        files = discover_files_walk(package_dir)

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

        files = discover_files_walk(package_dir)

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

        files = discover_files_walk(package_dir)

        assert files == sorted(files)

    def test_discover_files_uses_relative_paths(self, tmp_path):
        """Test that returned paths are relative to package_dir."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").touch()

        files = discover_files_walk(package_dir)

        # Should be relative, not absolute
        assert files[0] == Path("file.txt")
        assert not files[0].is_absolute()

    def test_discover_files_with_hidden_files(self, tmp_path):
        """Test that hidden files (starting with .) are discovered."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / ".hidden").touch()
        (package_dir / "visible").touch()

        files = discover_files_walk(package_dir)

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

        files = discover_files_walk(package_dir)

        assert Path("link.txt") in files

    def test_discover_symlinks_to_directories_without_traversal(self, tmp_path):
        """Test that symlinks to directories are discovered but not traversed."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Create directory outside package with a file inside
        external_dir = tmp_path / "external"
        external_dir.mkdir()
        (external_dir / "inside.txt").touch()

        # Create symlink to directory in package
        (package_dir / "dir_link").symlink_to(external_dir)
        (package_dir / "normal.txt").touch()

        files = discover_files_walk(package_dir)

        # Symlink to directory should be discovered
        assert Path("dir_link") in files
        assert Path("normal.txt") in files
        # But file inside linked directory should NOT be discovered
        assert Path("dir_link/inside.txt") not in files
        assert len(files) == 2

    def test_discover_symlink_and_target_in_same_package(self, tmp_path):
        """Test that both symlink and target are discovered when in package."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Create a regular file in package
        target_file = package_dir / ".bash_profile"
        target_file.touch()

        # Create symlink pointing to it within same package
        link_file = package_dir / ".bashrc"
        link_file.symlink_to(".bash_profile")

        files = discover_files_walk(package_dir)

        # Both the symlink and its target should be discovered
        assert Path(".bashrc") in files
        assert Path(".bash_profile") in files
        assert len(files) == 2


class TestShouldUseGit:
    """Tests for _should_use_git()."""

    def test_returns_true_for_git_repo(self, tmp_path):
        """Test that _should_use_git returns True for git repository."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        assert _should_use_git(package_dir) is True

    def test_returns_false_for_non_git_directory(self, tmp_path):
        """Test that _should_use_git returns False for non-git directory."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        assert _should_use_git(package_dir) is False

    def test_returns_true_for_subdirectory_of_git_repo(self, tmp_path):
        """Test _should_use_git returns True when package is subdirectory."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        # Initialize git repo at root
        subprocess.run(["git", "init"], cwd=repo_root, capture_output=True)

        # Check subdirectory
        package_dir = repo_root / "subdir"
        package_dir.mkdir()

        assert _should_use_git(package_dir) is True

    def test_returns_false_when_git_not_on_path(self, tmp_path):
        """Test _should_use_git returns False when git command not found."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert _should_use_git(package_dir) is False

    def test_returns_false_when_git_fails(self, tmp_path):
        """Test _should_use_git returns False when git command fails."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            assert _should_use_git(package_dir) is False


class TestDiscoverFilesGit:
    """Tests for discover_files_git()."""

    def test_discovers_tracked_files_only(self, tmp_path):
        """Test that only git-tracked files are discovered."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create files
        (package_dir / "tracked.txt").write_text("tracked")
        (package_dir / "untracked.txt").write_text("untracked")

        # Track only one file
        subprocess.run(["git", "add", "tracked.txt"], cwd=package_dir)

        files = discover_files_git(package_dir)

        assert Path("tracked.txt") in files
        assert Path("untracked.txt") not in files

    def test_respects_gitignore(self, tmp_path):
        """Test that .gitignore rules are respected."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create .gitignore
        (package_dir / ".gitignore").write_text("*.log\n")

        # Create files
        (package_dir / "file.txt").touch()
        (package_dir / "ignored.log").touch()

        # Add all files
        subprocess.run(["git", "add", "-A"], cwd=package_dir, capture_output=True)

        files = discover_files_git(package_dir)

        assert Path("file.txt") in files
        assert Path("ignored.log") not in files
        # .gitignore itself should be tracked
        assert Path(".gitignore") in files

    def test_filters_out_gitmodules(self, tmp_path):
        """Test that .gitmodules is filtered out."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create and track .gitmodules in root and subdirectory
        (package_dir / ".gitmodules").write_text("[submodule]\n")
        subdir = package_dir / "subdir"
        subdir.mkdir()
        (subdir / ".gitmodules").write_text("[submodule]\n")
        (package_dir / "file.txt").touch()

        subprocess.run(["git", "add", "-A"], cwd=package_dir, capture_output=True)

        files = discover_files_git(package_dir)

        assert Path(".gitmodules") not in files
        assert Path("subdir/.gitmodules") not in files
        assert Path("file.txt") in files

    def test_discovers_files_in_subdirectories(self, tmp_path):
        """Test that files in subdirectories are discovered."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create nested structure
        config_dir = package_dir / ".config"
        config_dir.mkdir()
        (config_dir / "settings.json").touch()

        subprocess.run(["git", "add", "-A"], cwd=package_dir, capture_output=True)

        files = discover_files_git(package_dir)

        assert Path(".config/settings.json") in files

    def test_returns_sorted_list(self, tmp_path):
        """Test that files are returned in sorted order."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create files in non-sorted order
        (package_dir / "zebra").touch()
        (package_dir / "apple").touch()
        (package_dir / "middle").touch()

        subprocess.run(["git", "add", "-A"], cwd=package_dir, capture_output=True)

        files = discover_files_git(package_dir)

        assert files == sorted(files)


class TestDiscoverFiles:
    """Tests for discover_files() wrapper."""

    def test_uses_git_for_git_repo(self, tmp_path):
        """Test that git method is used for git repositories."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=package_dir, capture_output=True)

        # Create files
        (package_dir / ".gitignore").write_text("*.log\n")
        (package_dir / "file.txt").touch()
        (package_dir / "ignored.log").touch()

        subprocess.run(["git", "add", "-A"], cwd=package_dir, capture_output=True)

        files = discover_files(package_dir)

        # Should use git (respects .gitignore)
        assert Path("file.txt") in files
        assert Path("ignored.log") not in files

    def test_uses_walk_for_non_git_directory(self, tmp_path):
        """Test that walk method is used for non-git directories."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()

        # Create files
        (package_dir / ".gitignore").write_text("*.log\n")
        (package_dir / "file.txt").touch()
        (package_dir / "ignored.log").touch()

        files = discover_files(package_dir)

        # Should use walk (does not respect .gitignore)
        assert Path("file.txt") in files
        assert Path("ignored.log") in files
        assert Path(".gitignore") in files

    def test_falls_back_to_walk_when_git_not_available(self, tmp_path):
        """Test fallback to walk when git is not on PATH."""
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        (package_dir / "file.txt").touch()

        with patch("haunt._files.discover._should_use_git", return_value=False):
            files = discover_files(package_dir)

        assert Path("file.txt") in files
