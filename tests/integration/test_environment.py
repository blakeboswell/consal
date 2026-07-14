"""Integration tests: hit real `gh`/`dco`/`devcontainer`, per EIGEN_GOALS.md's
testing strategy. Excluded from the default run (see `addopts` in
pyproject.toml).

Run these on the **host**, not inside this repo's own dev sandbox — the
sandbox has no Docker access by design (see the eigen-sandbox-no-docker
memory note), so `dco`/`devcontainer` aren't reachable from in there.
`scripts/run-integration-tests.sh` runs this tier and writes the output to
`.integration-results/latest.txt` for review.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.integration


def test_dco_is_on_path() -> None:
    assert shutil.which("dco") is not None, (
        "dco not found on PATH — this tier must run on the host, not in "
        "the sandbox this repo is developed in"
    )


def test_devcontainer_is_on_path() -> None:
    assert shutil.which("devcontainer") is not None, (
        "devcontainer CLI not found on PATH — install @devcontainers/cli "
        "on the host running this suite"
    )


def test_devcontainer_reports_a_version() -> None:
    result = subprocess.run(
        ["devcontainer", "--version"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert result.stdout.strip()


def test_gh_is_authenticated() -> None:
    result = subprocess.run(
        ["gh", "auth", "status"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_dco_supports_up_only() -> None:
    """`container.ensure_container_up` needs `dco --sub-config <name>
    --up-only`, a flag added to `dco` specifically for Eigen's headless
    bring-up (see the correction in EIGEN_GOALS.md's "Eigen/dco interface"
    decision — plain `dco` always attaches interactively and has no
    headless mode of its own). Fails until that flag has landed on the
    `dco` build installed on this host.
    """
    result = subprocess.run(["dco", "--help"], capture_output=True, text=True)
    # dco's usage() writes to stderr (die()/info()/usage() all do, per
    # dco.in), not stdout -- check both so this doesn't care which.
    help_text = result.stdout + result.stderr
    assert "--up-only" in help_text, (
        "dco --help doesn't mention --up-only yet — this host's dco build "
        "predates the flag Eigen's headless bring-up depends on"
    )


def test_anthropic_api_key_is_set() -> None:
    """Every Eigen-generated devcontainer.json injects
    `"ANTHROPIC_API_KEY": "${localEnv:ANTHROPIC_API_KEY}"` (see the
    correction in EIGEN_GOALS.md's "Eigen/dco interface" decision) so
    `claude -p` can authenticate headlessly instead of failing with
    "Not logged in" — found missing via a real run_turn integration test
    failure, not designed upfront. This env var has to actually be set on
    the host for that to work.
    """
    assert os.environ.get("ANTHROPIC_API_KEY"), (
        "ANTHROPIC_API_KEY is not set on this host — every Eigen-managed "
        "container's containerEnv references it via "
        "${localEnv:ANTHROPIC_API_KEY}, so claude -p will fail with "
        "'Not logged in' inside any container built without it"
    )
