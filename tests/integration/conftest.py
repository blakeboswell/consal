"""Shared fixtures for the integration test tier."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from consal.config import generate_subconfig
from consal.container import ensure_container_up

SUBCONFIG_NAME = "consal"


@dataclass(frozen=True)
class ManagedProject:
    """Bundles what `run_turn`/`ensure_container_up` both need, so tests
    using `consal_managed_project` don't have to import or hardcode the
    sub-config name separately from the project root.
    """

    root: Path
    subconfig_name: str


@pytest.fixture
def consal_managed_project(tmp_path: Path) -> Iterator[ManagedProject]:
    """A disposable git repo with a real Consal-generated sub-config
    (.devcontainer/consal/, .claude/settings.json with the guardrail hook
    registered) and a live container already up, via the real
    `config.generate_subconfig` + `container.ensure_container_up`.

    Distinct from `.devcontainer/consal-test/`: that fixture's copy of
    guardrail-hook.sh is inert (no .claude/settings.json wiring it up),
    kept only to satisfy `validate_subconfig`. This fixture is for tests
    that need the whole thing working end to end, not just container
    bring-up mechanics.

    Initializes tmp_path as a git repo with one commit on `main` before
    generating the sub-config: dco's git-identity sync and the guardrail
    hook's branch-detection logic both expect a real repo, and
    `git rev-parse --abbrev-ref HEAD` fails (falls back to the literal
    string "HEAD") on an unborn branch with zero commits, verified
    directly, see test_guardrail_hook.py.

    Tears down the container and its volumes (`dco --purge`) after the
    test, since each test gets a fresh tmp_path and therefore a distinct
    DCO_PROJECT_ID. Without this, repeated integration test runs would
    accumulate orphaned containers/volumes on the host indefinitely.
    """
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "consal-test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.name", "Consal Integration Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
    )

    generate_subconfig(tmp_path, SUBCONFIG_NAME)
    ensure_container_up(tmp_path, SUBCONFIG_NAME)

    try:
        yield ManagedProject(root=tmp_path, subconfig_name=SUBCONFIG_NAME)
    finally:
        subprocess.run(
            ["dco", str(tmp_path), "--sub-config", SUBCONFIG_NAME, "--purge"],
            input="y\n",
            capture_output=True,
            text=True,
        )
