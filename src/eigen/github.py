"""Thin wrapper over the `gh` CLI for issue/PR/comment operations.

Eigen shells out to `gh` rather than depending on a GitHub API library —
matches `dco`'s own pattern of shelling out to external tools, and keeps
Eigen's runtime dependency footprint at stdlib + subprocess only (see
EIGEN_GOALS.md, "Distribution model").
"""

from __future__ import annotations


def list_open_issues(repo: str) -> list[dict]:
    """List open issues for ``repo`` (e.g. "owner/name"). Not yet implemented."""
    raise NotImplementedError


def create_issue(repo: str, title: str, body: str) -> dict:
    """Create an issue in ``repo``. Not yet implemented."""
    raise NotImplementedError


def comment_on_issue(repo: str, issue_number: int, body: str) -> None:
    """Post a comment on an issue. Not yet implemented."""
    raise NotImplementedError
