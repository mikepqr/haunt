"""Output formatting for haunt operations."""

from datetime import datetime
from pathlib import Path

import typer

from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import PackageNotFoundError
from haunt.models import ConflictMode
from haunt.models import CorrectSymlinkConflict
from haunt.models import DirectoryConflict
from haunt.models import InstallPlan
from haunt.models import UninstallPlan


def print_install_plan(
    plan: InstallPlan,
    on_conflict: ConflictMode = ConflictMode.ABORT,
    dry_run: bool = False,
) -> None:
    """Print install plan to stdout.

    Args:
        plan: InstallPlan to print
        on_conflict: How conflicts are being handled
        dry_run: If True, use "Would" language instead of present tense
    """
    action_verb = "Would create" if dry_run else "Creating"
    replace_verb = "Would replace" if dry_run else "Replacing"
    past_verb = "would be created" if dry_run else "created"
    past_replace_verb = "would be replaced" if dry_run else "replaced"

    # Categorize conflicts
    already_correct = [
        c for c in plan.conflicts if isinstance(c, CorrectSymlinkConflict)
    ]
    num_already_correct = len(already_correct)

    # In FORCE mode, determine which symlinks are replacements vs new
    conflict_paths = {
        c.path for c in plan.conflicts if not isinstance(c, CorrectSymlinkConflict)
    }
    new_symlinks = [
        s for s in plan.symlinks_to_create if s.link_path not in conflict_paths
    ]
    replaced_symlinks = [
        s for s in plan.symlinks_to_create if s.link_path in conflict_paths
    ]

    # Show new symlinks being created
    if new_symlinks:
        typer.secho(f"{action_verb} symlinks:", fg=typer.colors.BRIGHT_BLACK)
        for symlink in new_symlinks:
            link_display = _display_path(symlink.link_path)
            source_display = _display_path(symlink.source_path)
            typer.secho(
                f"  {link_display} -> {source_display}", fg=typer.colors.BRIGHT_BLACK
            )

    # Show replacements in force mode
    if replaced_symlinks and on_conflict == ConflictMode.FORCE:
        typer.secho(f"{replace_verb} files/symlinks:", fg=typer.colors.BRIGHT_BLACK)
        for symlink in replaced_symlinks:
            link_display = _display_path(symlink.link_path)
            source_display = _display_path(symlink.source_path)
            typer.secho(
                f"  {link_display} -> {source_display}", fg=typer.colors.BRIGHT_BLACK
            )

    # Show already-correct symlinks
    if already_correct:
        typer.secho("Already correct:", fg=typer.colors.BRIGHT_BLACK)
        for conflict in already_correct:
            link_display = _display_path(conflict.path)
            # points_to is relative, resolve it to absolute for display
            absolute_source = (conflict.path.parent / conflict.points_to).resolve()
            source_display = _display_path(absolute_source)
            typer.secho(
                f"  {link_display} -> {source_display}", fg=typer.colors.BRIGHT_BLACK
            )

    # Summary line
    num_new = len(new_symlinks)
    num_replaced = len(replaced_symlinks)
    parts = []
    if num_new > 0:
        parts.append(f"{num_new} symlink{'s' if num_new != 1 else ''} {past_verb}")
    if num_replaced > 0 and on_conflict == ConflictMode.FORCE:
        parts.append(f"{num_replaced} {past_replace_verb}")
    if num_already_correct > 0:
        parts.append(f"{num_already_correct} already correct")

    summary = ", ".join(parts) if parts else "no changes"
    action = "Would install" if dry_run else "Installed"
    typer.secho(
        f"✓ {action} {plan.package_name} ({summary})", fg=typer.colors.GREEN, bold=True
    )


def print_uninstall_plan(plan: UninstallPlan, dry_run: bool = False) -> None:
    """Print uninstall plan to stdout.

    Args:
        plan: UninstallPlan to print
        dry_run: If True, use "Would" language instead of present tense
    """
    action_verb = "Would remove" if dry_run else "Removing"
    past_verb = "would be removed" if dry_run else "removed"

    # Show symlinks being removed
    if plan.symlinks_to_remove:
        typer.secho(f"{action_verb} symlinks:", fg=typer.colors.BRIGHT_BLACK)
        for symlink in plan.symlinks_to_remove:
            link_display = _display_path(symlink.link_path)
            typer.secho(f"  {link_display}", fg=typer.colors.BRIGHT_BLACK)

    # Show missing symlinks
    if plan.missing_symlinks:
        typer.secho("Missing:", fg=typer.colors.BRIGHT_BLACK)
        for missing_path in plan.missing_symlinks:
            link_display = _display_path(missing_path)
            typer.secho(f"  {link_display}", fg=typer.colors.BRIGHT_BLACK)

    # Show modified symlinks (exist but point to wrong target)
    if plan.modified_symlinks:
        typer.secho("Skipped (modified):", fg=typer.colors.BRIGHT_BLACK)
        for symlink in plan.modified_symlinks:
            link_display = _display_path(symlink.link_path)
            typer.secho(f"  {link_display}", fg=typer.colors.BRIGHT_BLACK)

    # Summary line
    num_removed = len(plan.symlinks_to_remove)
    parts = [f"{num_removed} symlink{'s' if num_removed != 1 else ''} {past_verb}"]
    if plan.missing_symlinks:
        num_missing = len(plan.missing_symlinks)
        parts.append(f"{num_missing} missing")
    if plan.modified_symlinks:
        num_modified = len(plan.modified_symlinks)
        parts.append(f"{num_modified} skipped (modified)")

    summary = ", ".join(parts)
    action = "Would uninstall" if dry_run else "Uninstalled"
    typer.secho(
        f"✓ {action} {plan.package_name} ({summary})", fg=typer.colors.GREEN, bold=True
    )


def print_conflict_error(error: ConflictError, on_conflict: ConflictMode) -> None:
    """Print conflict error to stderr.

    Args:
        error: ConflictError with list of conflicts
        on_conflict: The conflict mode that was used
    """
    typer.secho("✗ Conflicts detected:", fg=typer.colors.RED, bold=True, err=True)
    for conflict in error.conflicts:
        conflict_type = type(conflict).__name__.replace("Conflict", "").lower()
        typer.secho(f"  {conflict.path} ({conflict_type})", err=True)

    # Suggest resolution based on conflict types
    has_directories = any(isinstance(c, DirectoryConflict) for c in error.conflicts)
    if has_directories:
        typer.secho(
            "\nDirectory conflicts require manual resolution (cannot be forced)",
            err=True,
        )
    elif on_conflict == ConflictMode.ABORT:
        typer.secho(
            "\nRun with --on-conflict=skip or --on-conflict=force",
            err=True,
        )


def _display_path(path: Path) -> str:
    """Format path with ~ for home directory."""
    try:
        # Try to make it relative to home
        home = Path.home()
        rel_path = path.relative_to(home)
        return f"~/{rel_path}"
    except ValueError:
        # Not under home, return as-is
        return str(path)


def print_package_list(
    registry: Registry,
    package_name: str | None = None,
    verbose: bool = False,
) -> None:
    """Print list of installed packages with optional filtering.

    Args:
        registry: Registry containing installed packages
        package_name: Optional package name to filter to
        verbose: If True, show all symlinks with status validation

    Raises:
        PackageNotFoundError: If package_name specified but not found
    """
    if package_name:
        if package_name not in registry.packages:
            raise PackageNotFoundError(
                f"Package '{package_name}' not found in registry"
            )
        packages_to_show = {package_name: registry.packages[package_name]}
    else:
        packages_to_show = registry.packages

    if not packages_to_show:
        typer.secho("No packages installed", fg=typer.colors.BRIGHT_BLACK)
        return

    for name, entry in packages_to_show.items():
        typer.secho(name, bold=True)

        package_display = _display_path(entry.package_dir)
        typer.echo(f"  Package: {package_display}")

        target_display = _display_path(entry.target_dir)
        typer.echo(f"  Target: {target_display}")

        try:
            dt = datetime.fromisoformat(entry.installed_at)
            local_dt = dt.astimezone()
            timestamp = local_dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError):
            timestamp = entry.installed_at
        typer.echo(f"  Installed: {timestamp}")

        if not verbose:
            count = len(entry.symlinks)
            typer.echo(f"  Symlinks: {count}")
        else:
            correct_symlinks = []
            inconsistent_symlinks = []

            for symlink in entry.symlinks:
                link_display = _display_path(symlink.link_path)
                source_display = _display_path(symlink.source_path)

                if symlink.is_missing():
                    inconsistent_symlinks.append(
                        (
                            f"{link_display} -> {source_display} (link missing)",
                            typer.colors.RED,
                        )
                    )
                elif symlink.is_modified():
                    actual = symlink.get_actual_target()
                    if actual:
                        actual_display = _display_path(actual)
                        inconsistent_symlinks.append(
                            (
                                f"{link_display} -> {actual_display} "
                                f"(expected {source_display})",
                                typer.colors.YELLOW,
                            )
                        )
                    else:
                        inconsistent_symlinks.append(
                            (f"{link_display} (not a symlink)", typer.colors.RED)
                        )
                elif not symlink.source_exists():
                    inconsistent_symlinks.append(
                        (
                            f"{link_display} -> {source_display} (source file missing)",
                            typer.colors.YELLOW,
                        )
                    )
                else:
                    correct_symlinks.append(f"{link_display} -> {source_display}")

            typer.echo("  Symlinks:")

            if correct_symlinks:
                typer.echo("    Correct:")
                for symlink_str in correct_symlinks:
                    typer.secho(f"      {symlink_str}", fg=typer.colors.BRIGHT_BLACK)

            if inconsistent_symlinks:
                typer.echo("    Inconsistent with Registry:")
                for symlink_str, color in inconsistent_symlinks:
                    typer.secho(f"      {symlink_str}", fg=color)

                package_dir_display = _display_path(entry.package_dir)
                target_dir_display = _display_path(entry.target_dir)
                typer.echo()
                typer.secho("  To fix inconsistent symlinks:", fg=typer.colors.YELLOW)
                typer.secho(
                    f"    haunt install {package_dir_display} {target_dir_display}",
                    fg=typer.colors.YELLOW,
                )

        typer.echo()
