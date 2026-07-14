"""The autonomous loop: decide what's next, dispatch a turn, record the result.

Lesson carried forward (EIGEN_GOALS.md): idle and working must never look
identical from outside. Because turns run through `container.run_turn` (a
synchronous subprocess with a real exit code), the loop always has an
explicit success/failure to act on rather than needing to poll and guess.
"""

from __future__ import annotations

from pathlib import Path


def next_turn(project_id: str) -> str | None:
    """Return the prompt for the next turn to run, or None if idle.

    Not yet implemented.
    """
    raise NotImplementedError


def run_loop_once(project_id: str, workspace_folder: Path) -> None:
    """Run a single scheduler tick: pick work, dispatch it, record the result.

    Not yet implemented.
    """
    raise NotImplementedError
