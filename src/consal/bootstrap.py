"""Bootstrap a brand-new consal project: local git init, sub-config
generation, and GitHub repo creation, in that order; plus the
existing-project counterpart, detecting a repo already configured as the
workspace's git 'origin' remote.

Kept separate from `config.py` (sub-config generation/validation only)
and `github.py` (gh wrappers for issues/PRs/comments): this module's job
is orchestrating those two into one first-run flow, not owning either
concern itself.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from consal import config, github


def _origin_remote_url(workspace: Path) -> str | None:
    """The raw URL git's 'origin' remote points at, or `None` if this
    workspace isn't a git repo yet, or has no 'origin' remote.
    """
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def create_project(
    workspace: Path, subconfig_name: str, repo: str, visibility: str = "private"
) -> Path:
    """Bootstrap a brand-new consal project end to end: `git init` the
    workspace if needed, generate the sub-config, commit exactly that,
    then create ``repo`` on GitHub from that commit and push it.

    Raises `RuntimeError` if an `origin` remote already exists (regardless
    of whether it points at GitHub): this path is for brand-new projects
    only, never for re-pointing an existing repo (use plain `consal init`,
    which detects and adopts an existing remote instead, for that case).

    Never forks an existing repository -- always creates a brand-new,
    empty-except-for-the-sub-config repo.
    """
    if _origin_remote_url(workspace) is not None:
        raise RuntimeError(
            f"{workspace} already has an 'origin' remote; --create is for "
            "brand-new projects only. Run plain `consal init` to adopt the "
            "existing remote instead."
        )

    if not (workspace / ".git").is_dir():
        subprocess.run(["git", "init"], cwd=workspace, check=True)

    subconfig_dir = config.generate_subconfig(workspace, subconfig_name)

    subprocess.run(
        [
            "git",
            "add",
            str(subconfig_dir.relative_to(workspace)),
            str((workspace / ".claude" / "settings.json").relative_to(workspace)),
        ],
        cwd=workspace,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "consal: initial sub-config"],
        cwd=workspace,
        check=True,
    )

    github.create_repo(repo, workspace, visibility)
    return subconfig_dir


def detect_origin_repo(workspace: Path) -> str | None:
    """Return the ``owner/name`` this workspace's git 'origin' remote
    already points at, or `None` (not a git repo yet, or no 'origin' set).

    Parses both GitHub remote URL forms: `https://github.com/owner/name.git`
    and `git@github.com:owner/name.git`.
    """
    url = _origin_remote_url(workspace)
    if url is None:
        return None

    match = re.search(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?$", url)
    return match.group("repo") if match else None
