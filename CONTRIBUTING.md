# Contributing to haunt

Thank you for your interest in contributing to haunt!

## Development Setup

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Clone the repository:

```bash
git clone https://github.com/mikepqr/haunt.git
cd haunt
```

## Running Checks Locally

Before submitting a PR, ensure all checks pass locally. This saves time by catching issues before CI runs.

### Run All Checks

Run everything that CI will check:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=haunt --cov-report=term-missing
```

### Individual Commands

**Linting:**
```bash
uv run ruff check .
```

**Auto-fix linting issues:**
```bash
uv run ruff check --fix .
```

**Format code:**
```bash
uv run ruff format .
```

**Type checking:**
```bash
uv run mypy
```

**Tests:**
```bash
uv run pytest
```

**Tests with coverage:**
```bash
uv run pytest --cov=haunt --cov-report=term-missing
```

## Pre-commit Hooks (Optional)

You can install pre-commit hooks to run checks automatically before each commit:

```bash
uv tool install pre-commit
pre-commit install
```

The hooks will run ruff (linting and formatting) and mypy (type checking) on staged files.

## Code Standards

- **Python version:** 3.12+ required
- **Type hints:** All functions must be fully typed (mypy strict mode)
- **Formatting:** Ruff with 88 character line length
- **Imports:** One import per line (enforced by ruff's isort config)
- **Tests:** Maintain or improve code coverage

## CI Pipeline

GitHub Actions will run on all PRs:
- Ruff linting and format checking
- mypy type checking (strict mode)
- pytest with coverage on Python 3.12 and 3.13
- Tests run on both Ubuntu and macOS

All checks must pass before merging.

## Releases

Releases are managed through git tags and GitHub Releases. The version is maintained in `pyproject.toml` only (single source of truth).

### Version Format

Between releases, the version uses PEP 440 dev format (e.g., `0.2.0.dev0`). This indicates unreleased code.

### Release Process

1. **Remove the `.dev0` suffix:**
   ```bash
   # Edit pyproject.toml: version = "0.2.0.dev0" → version = "0.2.0"
   git add pyproject.toml
   git commit -m "Release v0.2.0"
   git push
   ```

2. **Tag and push the release:**
   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. **Create GitHub Release:**
   - Go to https://github.com/mikepqr/haunt/releases/new
   - Select the tag you just pushed
   - Publish the release

   This triggers the GitHub Action that builds and publishes to PyPI.

4. **Bump to next dev version:**
   ```bash
   # Edit pyproject.toml: version = "0.2.0" → version = "0.2.1.dev0"
   git add pyproject.toml
   git commit -m "Bump to v0.2.1.dev0"
   git push
   ```

The GitHub Action will fail if you try to release a dev version.

## Questions?

Open an issue at https://github.com/mikepqr/haunt/issues
