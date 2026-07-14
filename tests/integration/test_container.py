"""Integration tests: real `dco`/`devcontainer`, per EIGEN_GOALS.md's
testing strategy. Excluded from the default run (see `addopts` in
pyproject.toml); run on the host via scripts/run-integration-tests.sh, not
inside this repo's own dev sandbox (see the eigen-sandbox-no-docker memory
note).

Depends on `dco --up-only` (see EIGEN_GOALS.md's "Eigen/dco interface"
correction) — will fail until that flag has landed on the host's `dco`
build. test_environment.py::test_dco_supports_up_only checks for that
directly; this module fails the same way but for real, by actually trying
to use it.

Uses the `.devcontainer/eigen-test/` fixture sub-config, not the (not yet
built) production "eigen" sub-config `config.generate_subconfig` will
produce — see that fixture's own README.md.

Note: an earlier version of `run_turn` omitted `--config` from its
`devcontainer exec` call and these two tests passed anyway — almost
certainly by accident, reaching an already-running default-profile
container on the real, persistent repo this ran against rather than the
`eigen-test` sub-config container `ensure_container_up` actually brought
up. Caught once a disposable-project fixture with no such fallback
container existed (see conftest.py's `eigen_managed_project`) — see the
correction in `container.py`'s `run_turn` docstring.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eigen.container import ensure_container_up, run_turn

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ensure_container_up_and_run_turn_against_fixture() -> None:
    ensure_container_up(REPO_ROOT, "eigen-test")

    result = run_turn(REPO_ROOT, "eigen-test", "Respond with exactly one word: pong")

    assert result.succeeded, (
        f"run_turn failed (exit {result.exit_code})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "pong" in result.stdout.lower()


def test_run_turn_reports_failure_without_raising() -> None:
    """An empty prompt makes `claude -p` itself exit nonzero (verified
    directly in this sandbox: `claude -p ""` -> exit 1, "Input must be
    provided ..."). That failure should come back as a failed TurnResult,
    not raise — the whole point of routing turns through `devcontainer
    exec` rather than `dco --claude` is an explicit success/failure signal
    for the scheduler, never an exception to catch (lesson #4 in
    EIGEN_GOALS.md).
    """
    ensure_container_up(REPO_ROOT, "eigen-test")

    result = run_turn(REPO_ROOT, "eigen-test", "")

    assert result.succeeded is False
    assert result.exit_code != 0
