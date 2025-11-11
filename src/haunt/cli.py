"""Command-line interface for haunt."""

from pathlib import Path
from typing import Annotated

import typer

from haunt import __version__
from haunt.exceptions import ConflictError
from haunt.exceptions import HauntError
from haunt.exceptions import PackageAlreadyInstalledError
from haunt.exceptions import PackageNotFoundError
from haunt.exceptions import RegistryValidationError
from haunt.exceptions import RegistryVersionError
from haunt.models import ConflictMode
from haunt.operations import compute_install_plan
from haunt.operations import compute_uninstall_plan
from haunt.operations import execute_install_plan
from haunt.operations import execute_uninstall_plan
from haunt.output import print_conflict_error
from haunt.output import print_install_plan
from haunt.output import print_uninstall_plan
from haunt.registry import Registry

app = typer.Typer(help="Symlink dotfiles manager")


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

    try:
        plan = compute_install_plan(package, target, on_conflict=on_conflict)
        print_install_plan(plan, on_conflict=on_conflict, dry_run=dry_run)

        if not dry_run:
            execute_install_plan(plan, Registry.default_path(), on_conflict=on_conflict)
    except PackageAlreadyInstalledError as e:
        typer.secho(f"✗ {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None
    except ConflictError as e:
        print_conflict_error(e, on_conflict)
        raise typer.Exit(1) from None
    except (RegistryValidationError, RegistryVersionError) as e:
        typer.secho(f"✗ Registry error: {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None
    except PermissionError as e:
        typer.secho(
            f"✗ Permission denied: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1) from None
    except FileExistsError as e:
        typer.secho(
            f"✗ File exists (filesystem changed between planning and execution): {e}",
            fg=typer.colors.RED,
            bold=True,
            err=True,
        )
        typer.secho(
            "   Warning: Package may be partially installed. Check "
            "filesystem and registry manually.",
            err=True,
        )
        raise typer.Exit(1) from None
    except ValueError as e:
        typer.secho(f"✗ {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None
    except OSError as e:
        typer.secho(
            f"✗ Filesystem error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        typer.secho(
            "   Warning: Package may be partially installed. Check "
            "filesystem and registry manually.",
            err=True,
        )
        raise typer.Exit(1) from None
    except HauntError as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None


@app.command()
def uninstall(
    package: Annotated[str, typer.Argument(help="Package name to uninstall")],
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-n", help="Show what would be done")
    ] = False,
) -> None:
    """Uninstall a package by removing symlinks."""
    try:
        plan = compute_uninstall_plan(package, Registry.default_path())
        print_uninstall_plan(plan, dry_run=dry_run)

        if not dry_run:
            execute_uninstall_plan(plan, Registry.default_path())
    except PackageNotFoundError as e:
        typer.secho(f"✗ {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None
    except (RegistryValidationError, RegistryVersionError) as e:
        typer.secho(f"✗ Registry error: {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None
    except PermissionError as e:
        typer.secho(
            f"✗ Permission denied: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        raise typer.Exit(1) from None
    except OSError as e:
        typer.secho(
            f"✗ Filesystem error: {e}", fg=typer.colors.RED, bold=True, err=True
        )
        typer.secho(
            "   Warning: Package may be partially uninstalled. Check "
            "filesystem and registry manually.",
            err=True,
        )
        raise typer.Exit(1) from None
    except HauntError as e:
        typer.secho(f"✗ Error: {e}", fg=typer.colors.RED, bold=True, err=True)
        raise typer.Exit(1) from None


def main() -> None:
    """Main entry point for the haunt CLI."""
    app()


if __name__ == "__main__":
    main()
