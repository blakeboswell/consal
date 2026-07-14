"""Proves the guardrail hook is present, executable, and produces correct
block/allow decisions inside a real, Eigen-generated container -- not
just that its logic is correct on this dev sandbox's plain bash
(test_guardrail_hook.py covers that). Uses the `eigen_managed_project`
fixture (conftest.py), which calls the real `config.generate_subconfig`
against a disposable project -- distinct from `.devcontainer/eigen-test/`,
whose hook copy is inert.

Deliberately invokes the hook script directly (same JSON-on-stdin
technique as test_guardrail_hook.py's unit tests), not through a full
`claude -p` conversational turn. An earlier version tried asking Claude
to actually attempt a force-push in natural language, and Claude's own
safety judgment declined the command before ever attempting the Bash
tool call -- the PreToolUse hook never got a chance to fire at all, so
that approach couldn't actually prove the hook works, only that the
model has good judgment (which is not what this test is for). Invoking
the real hook file at its real in-container path via
`container.exec_in_container` proves what actually matters here: the
file is present, executable, and produces the correct decision --
decoupled from whether a model can be talked into a risky action on any
given run.
"""

from __future__ import annotations

import json

import pytest

from eigen.container import TurnResult, exec_in_container

from .conftest import ManagedProject

pytestmark = pytest.mark.integration


def _run_hook_in_container(
    project: ManagedProject, tool_name: str, command: str | None = None
) -> TurnResult:
    tool_input: dict = {}
    if command is not None:
        tool_input["command"] = command
    payload = json.dumps(
        {"tool_name": tool_name, "tool_input": tool_input, "cwd": "/workspace"}
    )
    hook_path = f"/workspace/.devcontainer/{project.subconfig_name}/guardrail-hook.sh"
    return exec_in_container(
        project.root, project.subconfig_name, ["bash", hook_path], input=payload
    )


def test_guardrail_hook_present_and_blocks_force_push(
    eigen_managed_project: ManagedProject,
) -> None:
    result = _run_hook_in_container(
        eigen_managed_project, "Bash", "git push --force origin main"
    )
    # 2 specifically, not just nonzero: the hook's own documented
    # contract is "blocks via exit code 2 (stderr becomes Claude's
    # feedback)".
    assert result.exit_code == 2, (
        f"expected the hook to block (exit 2), got exit {result.exit_code}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "force" in result.stderr.lower()


def test_guardrail_hook_present_and_allows_ordinary_commands(
    eigen_managed_project: ManagedProject,
) -> None:
    result = _run_hook_in_container(eigen_managed_project, "Bash", "git status")
    assert result.exit_code == 0, (
        f"expected the hook to allow this (exit 0), got exit {result.exit_code}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
