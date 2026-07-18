"""The autonomous loop: decide what's next, dispatch a turn, record the result.

Lesson carried forward (CONSAL_GOALS.md): idle and working must never look
identical from outside. Because turns run through `container.run_turn` (a
synchronous subprocess with a real exit code), the loop always has an
explicit success/failure to act on rather than needing to poll and guess
— `run_loop_once` returns a `TickResult` for the same reason: a caller
must never have to infer "did anything happen this tick" from side
effects alone.

How often `run_loop_once` gets called (polling interval, cron, a
long-running loop) is deliberately out of scope for this module — same
"kept separate" reasoning as `prompts.py`'s own docstring: scheduling
policy and turn dispatch are different concerns.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from consal import container, github, prompts, state
from consal.container import TurnResult


@dataclass(frozen=True)
class TickResult:
    """Explicit outcome of one scheduler tick — `was_idle` is never left
    for a caller to infer from `turn` being `None` in some cases and not
    others.
    """

    issue_number: int | None
    turn: TurnResult | None

    @property
    def was_idle(self) -> bool:
        return self.issue_number is None


def next_turn(repo: str, active_issue_number: int | None) -> dict | None:
    """Pick the issue to work this tick, or None if there's nothing to do.

    Sticks with the currently active issue across ticks until it's no
    longer open on GitHub (closed by a human, presumably after merging
    its PR) — container reuse means a single issue's work can span
    multiple ticks, and jumping to a different issue mid-work on every
    tick would make no sense. Only picks a new issue once the active one
    has actually closed — checked against the live `list_open_issues`
    result, never trusting `active_issue_number` as ground truth on its
    own (so a manually reopened issue, or one closed out from under the
    scheduler, is always reflected correctly on the very next tick).

    New issues are picked oldest-first (by `createdAt`) — the simplest
    deterministic v1 policy. V1 scope (CONSAL_GOALS.md) has no
    issue-level gating or prioritization to layer on top of this yet.
    """
    open_issues = github.list_open_issues(repo)
    if not open_issues:
        return None

    if active_issue_number is not None:
        for issue in open_issues:
            if issue["number"] == active_issue_number:
                return issue
        # active issue closed since the last tick -- fall through and pick a new one

    return min(open_issues, key=lambda issue: issue["createdAt"])


def run_loop_once(
    project_id: str, workspace_folder: Path, repo: str, subconfig_name: str
) -> TickResult:
    """Run a single scheduler tick: pick work, dispatch it, record the result.

    Brings the container up on every tick, not just once before the loop
    starts — `dco --up-only` reconnects to an already-running container
    without rebuilding, so this is cheap, and it self-heals if the
    container died between ticks instead of silently depending on some
    earlier setup step having worked.
    """
    container.ensure_container_up(workspace_folder, subconfig_name)

    project_state_dir = state.state_dir(project_id)
    active_issue_number = state.read_active_issue(project_state_dir)

    issue = next_turn(repo, active_issue_number)
    if issue is None:
        state.write_active_issue(project_state_dir, None)
        return TickResult(issue_number=None, turn=None)

    state.write_active_issue(project_state_dir, issue["number"])

    prompt = prompts.prompt_for_issue(
        repo, issue["number"], issue["title"], issue["body"]
    )
    turn = container.run_turn(workspace_folder, subconfig_name, prompt)

    if not turn.succeeded:
        github.comment_on_issue(
            repo,
            issue["number"],
            f"Consal's autonomous turn on this issue failed (exit "
            f"{turn.exit_code}).\n\n```\n{turn.stderr}\n```",
        )

    return TickResult(issue_number=issue["number"], turn=turn)
