"""Output formatting for haunt operations."""

from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import typer

from haunt._files.symlinks import observe
from haunt._registry import Registry
from haunt.exceptions import ConflictError
from haunt.exceptions import PackageNotFoundError
from haunt.models import Action
from haunt.models import ConflictMode
from haunt.models import InstallPlan
from haunt.models import LinkState
from haunt.models import PackageEntry
from haunt.models import Symlink
from haunt.models import UninstallPlan
from haunt.operations.install import decide

_GREY = typer.colors.BRIGHT_BLACK

_STATE_DESCRIPTIONS = {
    LinkState.ABSENT: "link missing",
    LinkState.CORRECT: "correct",
    LinkState.FOREIGN_LINK: "symlink to another location",
    LinkState.BROKEN_LINK: "broken symlink",
    LinkState.FILE: "file",
    LinkState.DIRECTORY: "directory",
    LinkState.IS_SOURCE: "the package file itself, inside a symlinked directory",
    LinkState.PARENT_NOT_DIRECTORY: "a parent path is not a directory",
}


def _display_path(path: Path) -> str:
    """Format path with ~ for home directory."""
    if path == Path.home():
        return "~/"
    try:
        return f"~/{path.relative_to(Path.home())}"
    except ValueError:
        return str(path)


def _arrow(symlink: Symlink) -> str:
    link, source = _display_path(symlink.link_path), _display_path(symlink.source_path)
    return f"{link} -> {source}"


def _print_section(heading: str, lines: Iterable[str]) -> int:
    """Print a heading and indented lines, or nothing if there are no lines."""
    lines = list(lines)
    if lines:
        typer.secho(heading, fg=_GREY)
        for line in lines:
            typer.secho(f"  {line}", fg=_GREY)
    return len(lines)


def _print_summary(action: str, package_name: str, parts: Iterable[str]) -> None:
    summary = ", ".join(parts) or "no changes"
    typer.secho(
        f"✓ {action} {package_name} ({summary})", fg=typer.colors.GREEN, bold=True
    )


def print_install_plan(plan: InstallPlan, dry_run: bool = False) -> None:
    """Print what an install did, or with dry_run what it would do."""

    def with_action(action: Action) -> list[Symlink]:
        return [link.symlink for link in plan.links if link.action is action]

    def verb(done: str, would: str) -> str:
        return would if dry_run else done

    created = _print_section(
        f"{verb('Creating', 'Would create')} symlinks:",
        map(_arrow, with_action(Action.CREATE)),
    )
    replaced = _print_section(
        f"{verb('Replacing', 'Would replace')} files/symlinks:",
        map(_arrow, with_action(Action.REPLACE)),
    )
    removed = _print_section(
        f"{verb('Removing', 'Would remove')} symlinks:",
        (_display_path(symlink.link_path) for symlink in plan.symlinks_to_remove),
    )
    skipped = _print_section(
        "Skipped (conflicts):",
        (
            f"{_display_path(link.symlink.link_path)} "
            f"({_STATE_DESCRIPTIONS[link.state]})"
            for link in plan.links
            if link.action is Action.SKIP
        ),
    )
    kept = _print_section("Already correct:", map(_arrow, with_action(Action.KEEP)))

    be = verb("", "would be ")
    counts = [
        (created, f"symlink{'' if created == 1 else 's'} {be}created"),
        (replaced, f"{be}replaced"),
        (removed, f"{be}removed"),
        (skipped, "skipped"),
        (kept, "already correct"),
    ]
    _print_summary(
        verb("Installed", "Would install"),
        plan.package_name,
        (f"{count} {label}" for count, label in counts if count),
    )


def print_uninstall_plan(plan: UninstallPlan, dry_run: bool = False) -> None:
    """Print what an uninstall did, or with dry_run what it would do."""
    removed = _print_section(
        "Would remove symlinks:" if dry_run else "Removing symlinks:",
        (_display_path(symlink.link_path) for symlink in plan.symlinks_to_remove),
    )
    missing = _print_section("Missing:", map(_display_path, plan.missing_symlinks))
    modified = _print_section(
        "Skipped (modified):",
        (_display_path(symlink.link_path) for symlink in plan.modified_symlinks),
    )

    past_verb = "would be removed" if dry_run else "removed"
    parts = [f"{removed} symlink{'' if removed == 1 else 's'} {past_verb}"]
    if missing:
        parts.append(f"{missing} missing")
    if modified:
        parts.append(f"{modified} skipped (modified)")
    _print_summary(
        "Would uninstall" if dry_run else "Uninstalled", plan.package_name, parts
    )


def print_conflict_error(error: ConflictError) -> None:
    """Print the conflicts that blocked an install, and how to get past them."""
    typer.secho("✗ Conflicts detected:", fg=typer.colors.RED, bold=True, err=True)
    for conflict in error.conflicts:
        typer.secho(
            f"  {conflict.symlink.link_path} ({_STATE_DESCRIPTIONS[conflict.state]})",
            err=True,
        )

    forceable = [
        decide(conflict.state, ConflictMode.FORCE) is Action.REPLACE
        for conflict in error.conflicts
    ]
    typer.echo(err=True)
    if any(forceable):
        typer.secho("Run with --on-conflict=skip or --on-conflict=force", err=True)
    if not all(forceable):
        typer.secho(
            "Directories and paths inside symlinked directories are never replaced: "
            "resolve them manually or run with --on-conflict=skip",
            err=True,
        )


def _link_status(symlink: Symlink) -> tuple[str, str | None]:
    """Describe a registered symlink, with a colour if it is not as installed."""
    state = observe(symlink)
    link = _display_path(symlink.link_path)
    if state is LinkState.CORRECT:
        if symlink.source_path.exists():
            return _arrow(symlink), None
        return f"{_arrow(symlink)} (source file missing)", typer.colors.YELLOW
    if state in (LinkState.FOREIGN_LINK, LinkState.BROKEN_LINK):
        actual = _display_path(symlink.link_path.readlink())
        expected = _display_path(symlink.source_path)
        return f"{link} -> {actual} (expected {expected})", typer.colors.YELLOW
    if state in (LinkState.ABSENT, LinkState.PARENT_NOT_DIRECTORY):
        return f"{_arrow(symlink)} (link missing)", typer.colors.RED
    return f"{link} ({_STATE_DESCRIPTIONS[state]})", typer.colors.RED


def _print_symlink_statuses(entry: PackageEntry) -> None:
    statuses = [_link_status(symlink) for symlink in entry.symlinks]
    correct = [line for line, color in statuses if color is None]
    inconsistent = [(line, color) for line, color in statuses if color is not None]

    typer.echo("  Symlinks:")
    if correct:
        typer.echo("    Correct:")
        for line in correct:
            typer.secho(f"      {line}", fg=_GREY)
    if inconsistent:
        typer.echo("    Inconsistent with Registry:")
        for line, color in inconsistent:
            typer.secho(f"      {line}", fg=color)
        typer.echo()
        typer.secho("  To fix inconsistent symlinks:", fg=typer.colors.YELLOW)
        typer.secho(
            f"    haunt install {_display_path(entry.package_dir)} "
            f"{_display_path(entry.target_dir)}",
            fg=typer.colors.YELLOW,
        )


def _format_timestamp(installed_at: str) -> str:
    try:
        return (
            datetime.fromisoformat(installed_at)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
    except ValueError:
        return installed_at


def print_package_list(
    registry: Registry,
    package_name: str | None = None,
    verbose: bool = False,
) -> None:
    """Print installed packages, optionally just one, optionally with link status.

    Raises:
        PackageNotFoundError: If package_name specified but not found
    """
    if package_name is None:
        entries = list(registry.packages.values())
    elif package_name in registry.packages:
        entries = [registry.packages[package_name]]
    else:
        raise PackageNotFoundError(f"Package '{package_name}' not found in registry")

    if not entries:
        typer.secho("No packages installed", fg=_GREY)

    for entry in entries:
        typer.secho(entry.name, bold=True)
        typer.echo(f"  Package: {_display_path(entry.package_dir)}")
        typer.echo(f"  Target: {_display_path(entry.target_dir)}")
        typer.echo(f"  Installed: {_format_timestamp(entry.installed_at)}")
        if verbose:
            _print_symlink_statuses(entry)
        else:
            typer.echo(f"  Symlinks: {len(entry.symlinks)}")
        typer.echo()
