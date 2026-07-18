"""Thin wrapper over the `gh` CLI for issue/PR/comment operations.

Consal shells out to `gh` rather than depending on a GitHub API library —
matches `dco`'s own pattern of shelling out to external tools, and keeps
Consal's runtime dependency footprint at stdlib + subprocess only (see
CONSAL_GOALS.md, "Distribution model").

Every call here uses `check=True`: a `gh` failure (bad repo, auth, network)
is a hard error the caller needs to know about immediately, not a
business outcome to inspect — unlike `container.run_turn`, which
deliberately never raises because a turn's exit code *is* the result.
"""

from __future__ import annotations

import json
import subprocess

_ISSUE_LIST_FIELDS = "number,title,body,url,state,labels,createdAt,updatedAt"


def list_open_issues(repo: str) -> list[dict]:
    """List open issues for ``repo`` (e.g. "owner/name")."""
    result = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            _ISSUE_LIST_FIELDS,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def create_issue(repo: str, title: str, body: str) -> dict:
    """Create an issue in ``repo``, returning its number and URL.

    `gh issue create` has no `--json` output — unlike `gh issue list`,
    there's no structured-output flag for creation in this CLI version
    (a known, still-open gh limitation: cli/cli#11196). It just prints
    the created issue's URL to stdout, so the issue number is parsed from
    the URL's trailing path segment — the documented workaround.
    """
    result = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
        capture_output=True,
        text=True,
        check=True,
    )
    url = result.stdout.strip()
    number = int(url.rstrip("/").rsplit("/", 1)[-1])
    return {"number": number, "url": url}


def comment_on_issue(repo: str, issue_number: int, body: str) -> None:
    """Post a comment on an issue."""
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--repo", repo, "--body", body],
        check=True,
    )


def close_issue(repo: str, issue_number: int, reason: str = "not planned") -> None:
    """Close an issue. ``reason`` is `gh`'s own vocabulary: "completed" or
    "not planned" (its documented default meaning for the latter --
    cleanup of a disposable test issue, not real completed work).
    """
    subprocess.run(
        ["gh", "issue", "close", str(issue_number), "--repo", repo, "--reason", reason],
        check=True,
    )
