"""Integration test: the real `scheduler.run_loop_once` chain -- real
container bring-up, real `gh` reads, real state persistence -- against a
live GitHub repo. Excluded from the default run (see `addopts` in
pyproject.toml).

Deliberately mocks `container.run_turn` and `github.comment_on_issue`,
the same reasoning already applied twice elsewhere in this suite:
- `test_guardrail_enforcement.py` stopped trying to prove hook behavior
  through a live `claude -p` turn, because the model's own judgment is an
  uncontrollable confound a deterministic test can't depend on.
- `test_github.py` never exercises `create_issue`/`comment_on_issue` for
  real in a way that spams the actual project repo on every run.

Letting a real, unscoped `claude -p` turn "work" a live issue against
`blakeboswell/consal` combines both risks at once (uncontrolled model
behavior *and* a real mutating write), so this test keeps the real chain
up through issue *selection* (real `list_open_issues`, real prompt
construction from a real issue's real title/body, real state
persistence), and mocks only the two operations that would actually let
an open-ended agent turn loose or leave test noise on the repo.
"""

from __future__ import annotations

import shutil
from unittest.mock import patch

import pytest

from consal import github, state
from consal.container import TurnResult
from consal.scheduler import run_loop_once

from .conftest import ManagedProject

pytestmark = pytest.mark.integration

REPO = "blakeboswell/consal"
PROJECT_ID = "consal-scheduler-integration-test"


@pytest.fixture
def real_test_issue():
    """A real, disposable issue on the live project repo -- created before
    the test, closed after, regardless of outcome.
    """
    issue = github.create_issue(
        REPO,
        title="[integration test] consal scheduler dispatch",
        body=(
            "Disposable issue created by tests/integration/test_scheduler.py "
            "to verify scheduler.run_loop_once picks up and dispatches real "
            "GitHub issues correctly. Safe to ignore/close if seen outside "
            "an automated test run."
        ),
    )
    try:
        yield issue
    finally:
        github.close_issue(REPO, issue["number"])


@pytest.fixture
def clean_scheduler_state():
    """Guarantees `~/.consal/<PROJECT_ID>/` doesn't linger on the host
    after this test, regardless of outcome -- this integration tier's
    other fixture (`consal_managed_project`) tears down containers/volumes
    for the same reason; runtime state deserves the same treatment.
    """
    project_state_dir = state.state_dir(PROJECT_ID)
    try:
        yield project_state_dir
    finally:
        shutil.rmtree(project_state_dir, ignore_errors=True)


def test_run_loop_once_dispatches_a_real_issue(
    consal_managed_project: ManagedProject,
    real_test_issue: dict,
    clean_scheduler_state,
) -> None:
    # Pre-seed the active issue rather than relying on next_turn's
    # oldest-first tiebreak: blakeboswell/consal may have other real,
    # unrelated open issues at any given time, and this test must not
    # depend on the disposable test issue happening to be the oldest one.
    state.write_active_issue(clean_scheduler_state, real_test_issue["number"])

    with (
        patch("consal.scheduler.container.run_turn") as mock_run_turn,
        patch("consal.scheduler.github.comment_on_issue") as mock_comment,
    ):
        mock_run_turn.return_value = TurnResult(exit_code=0, stdout="", stderr="")

        result = run_loop_once(
            PROJECT_ID,
            consal_managed_project.root,
            REPO,
            consal_managed_project.subconfig_name,
        )

        mock_run_turn.assert_called_once()
        call_args = mock_run_turn.call_args[0]
        mock_comment.assert_not_called()

    assert result.issue_number == real_test_issue["number"]
    assert result.was_idle is False
    assert call_args[0] == consal_managed_project.root
    assert call_args[1] == consal_managed_project.subconfig_name
    assert "[integration test] consal scheduler dispatch" in call_args[2]
    assert str(real_test_issue["number"]) in call_args[2]

    assert state.read_active_issue(clean_scheduler_state) == real_test_issue["number"]
