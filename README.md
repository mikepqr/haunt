# haunt

A dotfiles symlink manager.

## Installation

```bash
# Run directly with uvx (no install needed)
uvx haunt ~/.dotfiles

# Or install globally with uv
uv tool install haunt

# Or install with pip
pip install haunt
```

## Usage

```bash
haunt --help
```

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
