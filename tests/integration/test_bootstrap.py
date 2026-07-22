"""Integration tests: real `git`/`gh` against a real, disposable GitHub
repo, per CONSAL_GOALS.md's testing strategy. Excluded from the default
run (see `addopts` in pyproject.toml); run on the host via
scripts/run-integration-tests.sh.

`test_create_project_creates_real_repo_and_pushes` is the one test here
that actually mutates GitHub: it creates a real repo (via the
`disposable_repo` fixture, conftest.py) and deletes it afterward. The
other two tests exercise real `git` only -- no network, no repo left
behind -- so they're colocated here rather than split into the fast unit
tier, matching this repo's "one test file per module" layout
(bootstrap.py <-> test_bootstrap.py).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from consal import bootstrap

pytestmark = pytest.mark.integration


def test_create_project_creates_real_repo_and_pushes(disposable_repo: str) -> None:
    view = subprocess.run(
        ["gh", "repo", "view", disposable_repo, "--json", "visibility"],
        capture_output=True,
        text=True,
        check=True,
    )
    # gh surfaces GitHub's GraphQL RepositoryVisibility enum verbatim
    # (PUBLIC/PRIVATE/INTERNAL, all-caps), not the REST API's lowercase form.
    assert json.loads(view.stdout)["visibility"] == "PRIVATE"

    contents = subprocess.run(
        ["gh", "api", f"repos/{disposable_repo}/contents/.devcontainer/consal/devcontainer.json"],
        capture_output=True,
        text=True,
    )
    assert contents.returncode == 0, (
        f"sub-config wasn't pushed to {disposable_repo}: {contents.stderr}"
    )


def test_create_project_raises_for_real_when_origin_already_exists(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "https://github.com/someone/somewhere.git"],
        check=True,
    )

    with pytest.raises(RuntimeError, match="already has an 'origin' remote"):
        bootstrap.create_project(tmp_path, "consal", "owner/new-repo")

    assert not (tmp_path / ".devcontainer").exists()


def test_detect_origin_repo_against_real_git_remote(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin", "https://github.com/blakeboswell/consal.git"],
        check=True,
    )

    assert bootstrap.detect_origin_repo(tmp_path) == "blakeboswell/consal"
