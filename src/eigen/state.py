"""Runtime state for an Eigen-managed project: active issue, loop status, logs.

Lives outside git, in a host-side `~/.eigen/<project_id>/` directory,
deliberately separate from the static sub-config profile checked into the
project's own repo — see EIGEN_GOALS.md, "Eigen/`dco` interface" >
profile-vs-runtime-state split.
"""

from __future__ import annotations

from pathlib import Path


def state_dir(project_id: str) -> Path:
    return Path.home() / ".eigen" / project_id


def read_active_issue(project_id: str) -> int | None:
    """Not yet implemented."""
    raise NotImplementedError


def write_active_issue(project_id: str, issue_number: int | None) -> None:
    """Not yet implemented."""
    raise NotImplementedError
