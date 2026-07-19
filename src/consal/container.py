"""Wrappers around `dco` and `devcontainer exec` for autonomous turns.

Interactive work (planning, direct intervention) goes through
`dco --claude` directly and never touches this module. See
CONSAL_GOALS.md, "Consal/`dco` interface". This module is only for
headless, autonomous turns: `dco --sub-config <name> --up-only` to ensure
the container is up (a small additive flag on `dco`; see CONSAL_GOALS.md's
"Consal/`dco` interface" decision; plain `dco` always attaches
interactively, it has no headless bring-up mode of its own), then
`devcontainer exec
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

    Raises `subprocess.CalledProcessError` if `dco` fails. Bringing the
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


def exec_in_container(
    workspace_folder: Path,
    subconfig_name: str,
    argv: list[str],
    input: str | None = None,
) -> TurnResult:
    """Run an arbitrary command inside a running container via
    `devcontainer exec --workspace-folder ... --config ...`.

    `run_turn` is the specific case of this for `claude -p <prompt>`; this
    lower-level entry point exists so other code (and tests, e.g.
    invoking the guardrail hook script directly with a synthetic
    tool-call payload on stdin, to test hook enforcement independent of
    whether a model actually attempts a given tool call) doesn't have to
    reconstruct the `--workspace-folder`/`--config` command shape itself.

    Deliberately does not raise on a nonzero exit, same reasoning as
    `run_turn`.
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
            *argv,
        ],
        input=input,
        capture_output=True,
        text=True,
    )
    return TurnResult(
        exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr
    )


def run_turn(workspace_folder: Path, subconfig_name: str, prompt: str) -> TurnResult:
    """Run one headless turn: `devcontainer exec --workspace-folder ...
    --config ... -- claude -p <prompt>`.

    `--config` must point at the exact devcontainer.json the running
    container was brought up with. `dco` always passes both
    `--workspace-folder` and `--config` to every `devcontainer exec` call
    (see `dco.in`). Omitting `--config` makes the CLI default to
    `.devcontainer/devcontainer.json` (the default profile) when matching
    which running container to attach to, which doesn't match a container
    brought up via a named `--sub-config` and fails with "Dev container
    not found".

    Deliberately does not raise on a nonzero exit. The whole point of
    going through `devcontainer exec` is that its exit code becomes the
    turn's explicit success/failure signal for the caller (the scheduler)
    to act on, not an exception to catch.
    """
    return exec_in_container(workspace_folder, subconfig_name, ["claude", "-p", prompt])
