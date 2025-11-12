# CLAUDE.md

AI-focused development guidelines for haunt. Read [CONTRIBUTING.md](CONTRIBUTING.md) first for setup, code standards, and CI details.

## Code Style & Organization

- Keep functions small and unit testable
- Don't add unrequested features
- All functions must be fully typed (mypy strict mode)
- Import modules at the top of files, never inside functions
- Comments and docstrings should add meaningful context, not restate what the code obviously does. Keep them up to date when code changes

## Testing

- All new functionality requires test coverage in `tests/`
- We don't write tests for `_cli/` modules
- Run `uv run pytest --cov=haunt --cov-report=term-missing` before committing

## Git & CI

- pre-commit hooks may modify your working copy. Add these to the commit and recommit. Be very careful not to amend the previous commit when doing this.
- All CI checks must pass before merging

## Documentation

- Update README.md for user-facing changes
- Don't create new documentation files unless explicitly requested
- Keep existing examples accurate

## Pull Requests

- Reference issues with "Fixes #N" or "Closes #N"

## Communication

- Ask clarifying questions rather than making assumptions
- Discuss trade-offs when multiple solutions exist
- Be explicit about uncertainties

## Project Context

See [README.md](README.md)
