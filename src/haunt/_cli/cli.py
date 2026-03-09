"""Command-line interface for haunt."""

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
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.exceptions import PackageNotFoundError
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
    if target is None:
        target = Path.home()

    partial_warning = (
        "Warning: Package may be partially installed. "
        "Check filesystem and registry manually."
    )
    try:
        plan = plan_install(package, target, on_conflict=on_conflict)
        print_install_plan(plan, on_conflict=on_conflict, dry_run=dry_run)

        if not dry_run:
            apply_install(plan, on_conflict=on_conflict)
    except PackageAlreadyInstalledError as e:
        _fatal(str(e))
    except ConflictError as e:
        print_conflict_error(e, on_conflict)
        raise typer.Exit(1) from None
    except (RegistryValidationError, RegistryVersionError) as e:
        _fatal(f"Registry error: {e}")
    except PermissionError as e:
        _fatal(f"Permission denied: {e}")
    except FileExistsError as e:
        _fatal(
            f"File exists (filesystem changed between planning and execution): {e}",
            partial_warning,
        )
    except ValueError as e:
        _fatal(str(e))
    except OSError as e:
        _fatal(f"Filesystem error: {e}", partial_warning)
    except HauntError as e:
        _fatal(f"Error: {e}")


@app.command()
def list(
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
    try:
        registry = Registry()
        print_package_list(registry, package_name=package, verbose=verbose)
    except PackageNotFoundError as e:
        _fatal(str(e))
    except (RegistryValidationError, RegistryVersionError) as e:
        _fatal(f"Registry error: {e}")
    except HauntError as e:
        _fatal(f"Error: {e}")


@app.command()
def uninstall(
    package: Annotated[str, typer.Argument(help="Package name to uninstall")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be done")
    ] = False,
) -> None:
    """Uninstall a package by removing symlinks."""
    try:
        plan = plan_uninstall(package)
        print_uninstall_plan(plan, dry_run=dry_run)

        if not dry_run:
            apply_uninstall(plan)
    except PackageNotFoundError as e:
        _fatal(str(e))
    except (RegistryValidationError, RegistryVersionError) as e:
        _fatal(f"Registry error: {e}")
    except PermissionError as e:
        _fatal(f"Permission denied: {e}")
    except OSError as e:
        _fatal(
            f"Filesystem error: {e}",
            "Warning: Package may be partially uninstalled. "
            "Check filesystem and registry manually.",
        )
    except HauntError as e:
        _fatal(f"Error: {e}")


def main() -> None:
    """Main entry point for the haunt CLI."""
    app()


if __name__ == "__main__":
    main()
