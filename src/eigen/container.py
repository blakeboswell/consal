"""Wrappers around `dco` and `devcontainer exec` for autonomous turns.

Interactive work (planning, direct intervention) goes through
`dco --claude` directly and never touches this module — see
EIGEN_GOALS.md, "Eigen/`dco` interface". This module is only for
headless, autonomous turns: `dco --sub-config <name> --up-only` to ensure
the container is up (a small additive flag on `dco` — see the correction
in EIGEN_GOALS.md; plain `dco` always attaches interactively, it has no
headless bring-up mode of its own), then `devcontainer exec
--workspace-folder ... --config ... -- claude -p "$PROMPT"` as a
synchronous foreground subprocess, so its exit code is the turn's
explicit success/failure signal (lesson carried forward: never let
success/failure be an accidental side effect).
"""

from __future__ import annotations

import subprocess
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


def ensure_container_up(workspace_folder: Path, subconfig_name: str) -> None:
    """Run `dco <workspace_folder> --sub-config <subconfig_name> --up-only`
    to bring the container up without attaching.

    Takes `workspace_folder` explicitly (matching `run_turn`) rather than
    relying on the calling process's cwd matching dco's positional `[path]`
    argument implicitly.

    Raises `subprocess.CalledProcessError` if `dco` fails — bringing the
    container up is a precondition for everything that follows, so failure
    here must stop the caller rather than be silently absorbed.
    """
    subprocess.run(
        [
            "dco",
            str(workspace_folder),
            "--sub-config",
            subconfig_name,
            "--up-only",
        ],
        check=True,
    )


def run_turn(workspace_folder: Path, subconfig_name: str, prompt: str) -> TurnResult:
    """Run one headless turn: `devcontainer exec --workspace-folder ...
    --config ... -- claude -p <prompt>`.

    `--config` must point at the exact devcontainer.json the running
    container was brought up with. `dco` always passes both
    `--workspace-folder` and `--config` to every `devcontainer exec` call
    (see `dco.in`) — omitting `--config` makes the CLI default to
    `.devcontainer/devcontainer.json` (the default profile) when matching
    which running container to attach to, which doesn't match a container
    brought up via a named `--sub-config` and fails with "Dev container
    not found". Found via a real integration test failure, not assumed —
    an earlier version of this function omitted --config and happened to
    pass against a long-lived project with an already-running default
    container to fall back onto by accident.

    Deliberately does not raise on a nonzero exit — the whole point of
    going through `devcontainer exec` is that its exit code becomes the
    turn's explicit success/failure signal for the caller (the scheduler)
    to act on, not an exception to catch.
    """
    config_path = workspace_folder / ".devcontainer" / subconfig_name / "devcontainer.json"
    result = subprocess.run(
        [
            "devcontainer",
            "exec",
            "--workspace-folder",
            str(workspace_folder),
            "--config",
            str(config_path),
            "--",
            "claude",
            "-p",
            prompt,
        ],
        capture_output=True,
        text=True,
    )
    return TurnResult(
        exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr
    )
