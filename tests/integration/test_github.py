"""Integration test: real `gh` CLI against a real repo. Excluded from the
default run (see `addopts` in pyproject.toml).

Only exercises `list_open_issues` (read-only) against `blakeboswell/consal`
itself. Deliberately doesn't exercise `create_issue`/`comment_on_issue`
here — those mutate a real repo, and doing that automatically on every
test run would litter the issue tracker with test noise. Their command
shapes are already verified against `gh --help`'s actual documented flags
in the mocked unit tests (tests/unit/test_github.py), which is where the
real risk was (gh issue create has no --json output, confirmed via
cli/cli#11196 — not something worth re-verifying live every run).
"""

from __future__ import annotations

import pytest

from consal.github import list_open_issues

pytestmark = pytest.mark.integration


def test_list_open_issues_against_real_repo() -> None:
    issues = list_open_issues("blakeboswell/consal")
    assert isinstance(issues, list)
