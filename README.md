# haunt

A dotfiles symlink manager. [GNU stow](https://www.gnu.org/software/stow/) in Python, with a registry.

## Installation

```bash
# Run directly with uvx (no install needed)
uvx haunt install ~/.dotfiles

# Or install globally with uv
uv tool install haunt

# Or install with pip
pip install haunt
```

## Dependencies

We recommend installing `haunt` with uv, which installs Python, haunt and its dependencies.

If you choose in install manually, `haunt` requires Python 3.12+.

## Quickstart

You have a home directory with some existing files, and a dotfiles package:
```
/Users/mike
├── .config
│   └── starship.toml
└── dotfiles
    ├── .bashrc
    └── .config
        └── nvim
            └── init.lua
```
A package is just a directory containing files you want to link to from your home directory.

To install the package:
```bash
$ haunt install ~/dotfiles
Creating symlinks:
  /Users/mike/.bashrc -> /Users/mike/dotfiles/.bashrc
  /Users/mike/.config/nvim/init.lua -> /Users/mike/dotfiles/.config/nvim/init.lua

2 symlinks created
```

The files in the package are symlinked from your home folder, and existing files are preserved.
```
/Users/mike
├── .bashrc -> dotfiles/.bashrc
├── .config
│   ├── nvim
│   │   └── init.lua -> ../../dotfiles/.config/nvim/init.lua
│   └── starship.toml
└── dotfiles
    ├── .bashrc
    └── .config
        └── nvim
            └── init.lua
```

Uninstall the package:
```bash
$ haunt uninstall dotfiles
Removing symlinks:
  /Users/mike/.bashrc
  /Users/mike/.config/nvim/init.lua

2 symlinks removed
```

## Commands

### `haunt install`

```bash
haunt install [OPTIONS] PACKAGE [TARGET]
```

- `PACKAGE` - directory containing files to symlink (required)
- `TARGET` - where to create symlinks (default: `$HOME`)
- `--dry-run, -n` - show what would happen without doing it
- `--on-conflict` - how to handle conflicts:
  - `abort` (default) - stop if any files exist
  - `skip` - skip conflicting files, install the rest
  - `force` - replace files/symlinks (but never directories)

### `haunt uninstall`

```bash
haunt uninstall [OPTIONS] PACKAGE
```

- `PACKAGE` - package name to uninstall (required)
- `--dry-run, -n` - show what would happen without doing it

### `haunt list`

```bash
haunt list [OPTIONS] [PACKAGE]
```

List installed packages with their symlinks.

- `PACKAGE` - show only this package (optional, shows all if omitted)
- `--verbose, -v` - show all symlinks with status validation

**Example output:**

```bash
$ haunt list
dotfiles
  Package: ~/dotfiles
  Target: ~/
  Installed: 2025-11-12 13:45:23
  Symlinks: 3

nvim-config
  Package: ~/nvim-config
  Target: ~/.config
  Installed: 2025-11-12 14:30:15
  Symlinks: 5
```

**Verbose mode** checks each symlink and reports issues:

```bash
$ haunt list --verbose dotfiles
dotfiles
  Package: ~/dotfiles
  Target: ~/
  Installed: 2025-11-12 13:45:23
  Symlinks:
    Correct
      ~/.bashrc -> ~/dotfiles/.bashrc
    Inconsistent with Registry
      ~/.vimrc -> ~/dotfiles/.vimrc (link missing)
      ~/.zshrc -> /other/file (expected ~/dotfiles/.zshrc)
      ~/.profile -> ~/dotfiles/.profile (source file missing)

  To fix inconsistent symlinks:
    haunt install ~/dotfiles ~/
```

Inconsistent symlink types:
- `(link missing)`: symlink doesn't exist at expected location
- `(expected ...)`: symlink points to wrong target
- `(source file missing)`: symlink exists but source file is gone

## Conflict handling

By default haunt aborts on any conflict:

```bash
$ echo "important config" > ~/.bashrc
$ haunt install ~/.dotfiles
✗ Conflicts detected:
  /Users/mike/.bashrc (file)
```

Use `--on-conflict=skip` to install non-conflicting files, or `--on-conflict=force` to replace files and broken symlinks.

`haunt` will never replace existing directories with symlinks, even with `--on-conflict=force`.

## Multiple packages

haunt creates symlinks to **files**, not directories. This lets multiple packages install into the same directory:

```
/Users/mike/dotfiles
├── shell
│   ├── .bashrc
│   └── .config
│       └── starship.toml
└── nvim
    └── .config
        └── nvim
            └── init.lua
```

Install both packages:
```bash
$ haunt install ~/dotfiles/shell
Creating symlinks:
  /Users/mike/.bashrc -> /Users/mike/dotfiles/shell/.bashrc
  /Users/mike/.config/starship.toml -> /Users/mike/dotfiles/shell/.config/starship.toml

2 symlinks created

$ haunt install ~/dotfiles/nvim
Creating symlinks:
  /Users/mike/.config/nvim/init.lua -> /Users/mike/dotfiles/nvim/.config/nvim/init.lua

1 symlink created
```

Result:
```
/Users/mike
├── .bashrc -> dotfiles/shell/.bashrc
└── .config
    ├── nvim
    │   └── init.lua -> ../../dotfiles/nvim/.config/nvim/init.lua
    └── starship.toml -> ../dotfiles/shell/.config/starship.toml
```

Both packages install files into `.config`. haunt creates real directories (not symlinks to directories), so this works fine.

Uninstalling one package leaves the other intact:
```bash
$ haunt uninstall shell
Removing symlinks:
  /Users/mike/.bashrc
  /Users/mike/.config/starship.toml

2 symlinks removed

# .config/nvim/init.lua remains untouched
```

## Adding and removing files from packages

To add a file to an already-installed package, copy or move it into the package directory (creating subdirectories as needed), then reinstall:

```bash
# Add a simple file
mv ~/.vimrc ~/dotfiles/.vimrc
haunt install ~/dotfiles

# Add a nested file (create directories first)
mkdir -p ~/dotfiles/.config/nvim
mv ~/.config/nvim/init.lua ~/dotfiles/.config/nvim/init.lua
haunt install ~/dotfiles
```

The reinstall detects the file is now missing from its original location and creates the symlink.

To remove a file from a package, delete it from the package directory, then uninstall and reinstall:

```bash
rm ~/dotfiles/.vimrc
haunt uninstall dotfiles
haunt install ~/dotfiles
```

## Git Integration

If your package is in a git repository, `haunt` automatically uses `git ls-files` to discover files. This means:

- ✅ `.gitignore` rules are respected automatically
- ✅ `.git` directory and `.gitmodules` are excluded
- ✅ Only tracked files are symlinked
- ✅ Files in submodules are discovered

For non-git packages (or if git is not available), `haunt` falls back to discovering all files in the directory tree.

## The Registry

`haunt` maintains state about the links it manages independently of the package directory. This means:

- ✅ `haunt uninstall` works even if the package directory was moved, deleted, or its contents modified
- ✅ Won't remove symlinks that have been manually modified to point elsewhere or replaced with files

**If you need to uninstall a package that's not in the registry:** Run `haunt install <package-dir>` first to detect existing symlinks and rebuild the registry entry, then `haunt uninstall <package-name>` will work normally.

The registry follows the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html):
- **Linux**: `~/.local/state/haunt/registry.json` (or `$XDG_STATE_HOME/haunt/registry.json`)
- **macOS**: `~/Library/Application Support/haunt/registry.json`

## How is this different from GNU stow?

[GNU stow](https://www.gnu.org/software/stow/) is the original. It's mature, battle-tested, and does folder tree merging.

The main differences:
- **No Perl dependency** - uses Python (ubiquitous on modern systems) and uv
- **Registry** - see [The Registry](#the-registry) section for benefits

The core symlinking behavior is the same as stow.

## How is this different from stowsh?

[stowsh](https://github.com/mikepqr/stowsh) is my bash implementation of stow.

`haunt` trades stowsh's zero dependencies for a [registry](#the-registry), maintainability and testability. If you want a single bash script with no dependencies, use stowsh!

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.

## License

MIT
