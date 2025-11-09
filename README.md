# haunt

A dotfiles symlink manager.

## Installation

```bash
# Run directly with uvx (no install needed)
uvx haunt

# Or install globally with uv
uv tool install haunt

# Or install with pip
pip install haunt
```

## Usage

```bash
haunt --help
```

## Why Python 3.12+?

This project requires Python 3.12 or later for the following features:

- **`Path.walk()`** - Used in `discover_files()` to recursively traverse package directories
- **`Path.relative_to(walk_up=True)`** - Used to compute relative symlink paths that can traverse up directories with `..` components

## Future Work

- **Transactional operations**: Currently if an error occurs partway through `execute_install_plan()` or `execute_uninstall_plan()`, the package may be left in an inconsistent state (partially installed with no registry entry, or vice versa). Possible solutions:
  - Implement rollback: if any symlink operation fails, undo all previous operations before updating registry
  - Add a `haunt repair` command to detect and fix inconsistent states (or make sure install and then uninstall does this)
- **Path traversal security validation**: Add `is_under_directory()` function to validate that discovered file paths don't escape the package/target directories using `..` components. This would prevent malicious packages from creating symlinks outside the intended directory.
- **Resolve the asymmetry/bad UX** that install takes a package path and uninstall takes a package name
    - Related: how to uninstall packages that aren't in the registry but we do have the source for
- **Construct stress tests to put it in inconsisent states**
- **README** that explains what it does and why it works the way it does
- **Implement** `haunt adopt` to add a file to a package

## Development

```bash
# Run tests
uv run pytest

# Run locally
uv run haunt --help

# Run with coverage
uv run pytest --cov=haunt --cov-report=term-missing
```

## License

MIT
