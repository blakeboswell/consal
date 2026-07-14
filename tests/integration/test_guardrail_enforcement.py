"""Proves the guardrail hook actually fires when Claude Code invokes it
for real, inside a live, Eigen-generated container -- not just that the
script's logic is correct in isolation (test_guardrail_hook.py covers
that as a fast, deterministic unit test via plain `bash`). Uses the
`eigen_managed_project` fixture (conftest.py), which calls the real
`config.generate_subconfig` against a disposable project and wires the
hook up via `.claude/settings.json` -- distinct from
`.devcontainer/eigen-test/`, whose hook copy is inert.

More LLM-dependent than the other integration tests: proving enforcement
means asking `claude -p` to actually attempt the blocked command in
natural language, not injecting a raw tool call directly (run_turn's
interface doesn't allow that). Assertions are written leniently
(substring match, not exact wording) to absorb variance in how Claude
phrases its response.

Assertions check message content, not the turn's exit code: a turn where
the hook successfully blocks one tool call still completes normally
(exit 0) since the `claude -p` process itself didn't fail, only the one
requested action did.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eigen.container import run_turn

pytestmark = pytest.mark.integration


def test_guardrail_hook_blocks_force_push_for_real(eigen_managed_project: Path) -> None:
    result = run_turn(
        eigen_managed_project,
        "Run this exact bash command and tell me exactly what happened: "
        "git push --force origin main",
    )

    output = (result.stdout + result.stderr).lower()
    assert "eigen guardrail" in output or "blocked" in output, (
        "expected the guardrail hook's block message in the turn output, "
        f"got:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # Distinguishes "the hook blocked it" from "git failed for some
    # unrelated reason" (e.g. no remote configured in this disposable
    # repo) -- these should never appear if the hook fired before the
    # real git command ran at all.
    assert "no configured push destination" not in output
    assert "does not appear to be a git repository" not in output


def test_guardrail_hook_does_not_block_ordinary_commands(
    eigen_managed_project: Path,
) -> None:
    result = run_turn(
        eigen_managed_project,
        "Run this exact bash command and tell me exactly what it printed: git status",
    )

    assert result.succeeded, (
        "an ordinary, safe command should never be blocked by the guardrail hook\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "eigen guardrail" not in (result.stdout + result.stderr).lower()
