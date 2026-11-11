"""Command-line interface for haunt."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated
from typing import NoReturn

import typer

from haunt import __version__
from haunt._cli.output import print_conflict_error
from haunt._cli.output import print_install_plan
from haunt._cli.output import print_package_list
from haunt._cli.output import print_uninstall_plan
from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import HauntError
from haunt.exceptions import RegistryValidationError
from haunt.exceptions import RegistryVersionError
from haunt.models import ConflictMode
from haunt.operations import apply_install
from haunt.operations import apply_uninstall
from haunt.operations import plan_install
from haunt.operations import plan_uninstall

app = typer.Typer(help="Symlink dotfiles manager")


def _fatal(msg: str, *extra: str) -> NoReturn:
    """Print red bold error to stderr, optional extra lines, and exit 1."""
    typer.secho(f"✗ {msg}", fg=typer.colors.RED, bold=True, err=True)
    for line in extra:
        typer.secho(f"   {line}", err=True)
    raise typer.Exit(1)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        typer.echo(f"haunt {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", callback=version_callback, is_eager=True, help="Show version"
        ),
    ] = None,
) -> None:
    """Symlink dotfiles manager."""
    pass


@contextmanager
def _exit_on_error(partial: str | None = None) -> Iterator[None]:
    """Turn expected errors into a message and exit status 1.

    Args:
        partial: Set while changing the filesystem ("installed" or
            "uninstalled"), so that an OS error warns about the half-done state.
    """
    try:
        yield
    except ConflictError as e:
        print_conflict_error(e)
        raise typer.Exit(1) from None
    except (RegistryValidationError, RegistryVersionError) as e:
        _fatal(f"Registry error: {e}")
    except (HauntError, ValueError) as e:
        _fatal(str(e))
    except PermissionError as e:
        _fatal(f"Permission denied: {e}")
    except OSError as e:
        if partial is None:
            _fatal(str(e))
        _fatal(
            f"Filesystem error: {e}",
            f"Warning: Package may be partially {partial}. "
            "Check filesystem and registry manually.",
        )


@app.command()
def install(
    package: Annotated[Path, typer.Argument(help="Package directory to install")],
    target: Annotated[
        Path | None,
        typer.Argument(help="Target directory for symlinks (default: $HOME)"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be done")
    ] = False,
    on_conflict: Annotated[
        ConflictMode,
        typer.Option(help="How to handle conflicting files"),
    ] = ConflictMode.ABORT,
) -> None:
    """Install a package by creating symlinks."""
    with _exit_on_error():
        plan = plan_install(package, target or Path.home(), on_conflict=on_conflict)
    if not dry_run:
        with _exit_on_error(partial="installed"):
            apply_install(plan)
    print_install_plan(plan, dry_run=dry_run)


@app.command("list")
def list_packages(
    package: Annotated[
        str | None,
        typer.Argument(help="Show only this package (optional)"),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show all symlinks with status"),
    ] = False,
) -> None:
    """List installed packages."""
    with _exit_on_error():
        print_package_list(Registry(), package_name=package, verbose=verbose)


@app.command()
def uninstall(
    package: Annotated[str, typer.Argument(help="Package name to uninstall")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be done")
    ] = False,
) -> None:
    """Uninstall a package by removing symlinks."""
    with _exit_on_error():
        plan = plan_uninstall(package)
    if not dry_run:
        with _exit_on_error(partial="uninstalled"):
            apply_uninstall(plan)
    print_uninstall_plan(plan, dry_run=dry_run)


def main() -> None:
    """Main entry point for the haunt CLI."""
    app()


if __name__ == "__main__":
    main()
