"""Integration test: `doctor.check_repo_access` against a real, disposable
GitHub repo (the `disposable_repo` fixture, conftest.py). Excluded from
the default run (see `addopts` in pyproject.toml).

The unit tests (tests/unit/test_doctor.py) already cover the branch logic
(unset PAT, nonzero `gh` exit, READ vs WRITE permission) against mocked
`subprocess.run`. What those can't prove is that the real `gh repo view
--json viewerPermission` invocation, with `GH_TOKEN` actually overridden
in a real subprocess environment, still works against the real `gh` CLI
and API -- that's what this file is for.

Never touches the host's own real `CONSAL_GH_PAT` (whatever it's actually
scoped to on this machine is unrelated to the disposable repo this test
creates): the "has access" case uses `gh auth token` (this host's own,
broader login, which does own the disposable repo) as a stand-in
correctly-scoped credential, and the "lacks access" case uses a
deliberately bogus token string, so both branches are exercised for real
without depending on, or risking, the project's actual production PAT.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from consal.doctor import check_repo_access
from consal.settings import Settings

pytestmark = pytest.mark.integration


def _settings(repo: str) -> Settings:
    # workspace is unused by check_repo_access; a placeholder is fine.
    return Settings(workspace=Path.cwd(), project_id="x", repo=repo, sub_config="consal")


def test_check_repo_access_passes_with_a_real_valid_token(
    disposable_repo: str, monkeypatch
) -> None:
    token = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True
    ).stdout.strip()
    monkeypatch.setenv("CONSAL_GH_PAT", token)

    assert check_repo_access(_settings(disposable_repo)) is True


def test_check_repo_access_fails_with_a_bogus_token(
    disposable_repo: str, monkeypatch
) -> None:
    monkeypatch.setenv("CONSAL_GH_PAT", "ghp_not_a_real_token_0000000000000000")

    assert check_repo_access(_settings(disposable_repo)) is False
