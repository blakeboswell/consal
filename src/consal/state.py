"""Runtime state for a Consal-managed project: active issue, loop status, logs.

Lives outside git, in a host-side `~/.consal/<project_id>/` directory,
deliberately separate from the static sub-config profile checked into the
project's own repo — see CONSAL_GOALS.md, "Consal/`dco` interface" >
profile-vs-runtime-state split.

`read_active_issue`/`write_active_issue` take the state directory itself
(a `Path`), not a bare `project_id`, so neither hides an implicit
`Path.home()` dependency the way an earlier version of `container.py`'s
`ensure_container_up` implicitly relied on the calling process's cwd —
found to be a real bug there. Callers who only have a `project_id` do
`read_active_issue(state_dir(project_id))`.
"""

from __future__ import annotations

from pathlib import Path


def state_dir(project_id: str) -> Path:
    return Path.home() / ".consal" / project_id


def _active_issue_file(state_dir: Path) -> Path:
    return state_dir / "active_issue"


def read_active_issue(state_dir: Path) -> int | None:
    """Return the currently active issue number, or None if none is set.

    Absence of the state file is the sole "no active issue" representation
    — read and write are kept symmetric on purpose, so there's exactly one
    way to represent "nothing active," not two (e.g. missing file vs.
    empty file) that could silently drift apart. A file that exists but
    doesn't parse as an int raises rather than being treated as "no active
    issue" — a corrupted state file must be a loud failure, not silently
    mistaken for a clean slate (lesson carried forward: explicit
    success/failure, never an accidental side effect).
    """
    path = _active_issue_file(state_dir)
    if not path.is_file():
        return None
    return int(path.read_text().strip())


def write_active_issue(state_dir: Path, issue_number: int | None) -> None:
    """Set (or, with None, clear) the currently active issue number."""
    path = _active_issue_file(state_dir)
    if issue_number is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{issue_number}\n")
