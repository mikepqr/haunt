"""Tests for decide(), the install conflict policy.

These state the policy as properties over every (state, mode) pair rather
than restating the table entry by entry.
"""

import pytest

from haunt.models import Action
from haunt.models import ConflictMode
from haunt.models import LinkState
from haunt.operations.install import decide

OCCUPIED = [s for s in LinkState if s not in (LinkState.ABSENT, LinkState.CORRECT)]


@pytest.mark.parametrize("mode", ConflictMode)
def test_absent_link_is_always_created(mode):
    assert decide(LinkState.ABSENT, mode) is Action.CREATE


@pytest.mark.parametrize("mode", ConflictMode)
def test_correct_link_is_always_kept(mode):
    assert decide(LinkState.CORRECT, mode) is Action.KEEP


@pytest.mark.parametrize("state", OCCUPIED)
def test_abort_blocks_on_anything_in_the_way(state):
    assert decide(state, ConflictMode.ABORT) is Action.BLOCK


@pytest.mark.parametrize("state", OCCUPIED)
def test_skip_leaves_anything_in_the_way_alone(state):
    assert decide(state, ConflictMode.SKIP) is Action.SKIP


def test_force_replaces_only_files_and_symlinks():
    """Directories, the package's own files and non-directory parents are
    never removed, whatever the mode."""
    replaced = {s for s in LinkState if decide(s, ConflictMode.FORCE) is Action.REPLACE}

    assert replaced == {LinkState.FILE, LinkState.FOREIGN_LINK, LinkState.BROKEN_LINK}


@pytest.mark.parametrize("state", OCCUPIED)
def test_force_blocks_on_whatever_it_will_not_replace(state):
    assert decide(state, ConflictMode.FORCE) in (Action.REPLACE, Action.BLOCK)


@pytest.mark.parametrize("state", LinkState)
@pytest.mark.parametrize("mode", [ConflictMode.ABORT, ConflictMode.SKIP])
def test_only_force_ever_replaces(state, mode):
    assert decide(state, mode) is not Action.REPLACE
