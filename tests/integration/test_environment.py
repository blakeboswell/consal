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
    assert "--up-only" in result.stdout, (
        "dco --help doesn't mention --up-only yet — this host's dco build "
        "predates the flag Eigen's headless bring-up depends on"
    )
