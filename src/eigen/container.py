"""Wrappers around `dco` and `devcontainer exec` for autonomous turns.

Interactive work (planning, direct intervention) goes through
`dco --claude` directly and never touches this module — see
EIGEN_GOALS.md, "Eigen/`dco` interface". This module is only for
headless, autonomous turns: `dco --sub-config <name>` to ensure the
container is up, then `devcontainer exec ... -- claude -p "$PROMPT"` as a
synchronous foreground subprocess, so its exit code is the turn's
explicit success/failure signal (lesson carried forward: never let
success/failure be an accidental side effect).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TurnResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


def ensure_container_up(subconfig_name: str) -> None:
    """Run `dco --sub-config <subconfig_name>` to bring the container up.

    Not yet implemented.
    """
    raise NotImplementedError


def run_turn(workspace_folder: Path, prompt: str) -> TurnResult:
    """Run one headless turn: `devcontainer exec ... -- claude -p <prompt>`.

    Not yet implemented.
    """
    raise NotImplementedError
