"""Prompt construction for autonomous turns.

Kept separate from `scheduler.py` so prompt wording can change without
touching dispatch/control-flow logic, and so it's independently unit
testable.
"""

from __future__ import annotations


def prompt_for_issue(repo: str, issue_number: int, issue_title: str, issue_body: str) -> str:
    """Build the prompt handed to `claude -p` for working a given issue.

    Doesn't repeat the guardrail hook's rules. Force-push, direct push to
    main/master, `gh pr merge`, etc. are already enforced at the tool-call
    level regardless of what this prompt says (CONSAL_GOALS.md's isolation
    goals: the hook is a backstop, not something to rely on the prompt to
    avoid triggering). It just points Claude at the intended workflow so
    it doesn't waste a turn hitting a guardrail it could have avoided:
    work on a branch, open a PR when done, let a human merge.
    """
    return f"""\
You are working autonomously on the GitHub repository {repo}.

Your task is issue #{issue_number}: "{issue_title}"

{issue_body}

Implement this issue. When you're done:
1. Commit your changes on a new branch (never main/master directly).
2. Push the branch and open a pull request referencing issue #{issue_number}.
3. Do not merge the pull request yourself. A human reviews and merges.

If the issue is unclear or you get stuck, leave a comment on issue
#{issue_number} explaining what's blocking you, rather than guessing.
"""


def prompt_for_decomposition(repo: str, plan_text: str) -> str:
    """Build the prompt handed to `claude -p` for decomposing the project
    plan into GitHub issues.

    Dispatched through the same `run_turn` mechanism as `prompt_for_issue`;
    per CONSAL_GOALS.md's "Plan decomposition" decision, the turn itself is
    the orchestrator, not Python-side orchestration logic. Effort scaling,
    sub-agent task boundaries, and the idempotency marker convention are
    all stated explicitly here rather than left for the model to infer,
    since vague delegation is a documented cause of duplicate work between
    sub-agents.
    """
    return f"""\
You are decomposing a project plan into GitHub issues for the repository
{repo}.

Here is the current plan:

{plan_text}

First, check the repository's existing issues (open and closed) so you
don't recreate work that's already tracked:

    gh issue list --repo {repo} --state all --json number,title,body

Each issue created from the plan carries a hidden marker at the top of
its body identifying which plan section it came from:

    <!-- consal-plan-ref: <slug> -->

where `<slug>` is a short, stable, lowercase-hyphenated identifier for
that section (e.g. "user-auth" or "cli-doctor-command"). Before creating
an issue for a plan section, check whether an issue carrying that
section's marker already exists. If one does, skip it: don't create a
duplicate, and don't edit or close it.

Break the plan into components, sub-components, and issues at the
granularity a human engineer would use. If the plan has more than a
handful of largely independent top-level components, use sub-agents to
evaluate each one in parallel against the existing issue list, then
synthesize the results before creating anything: give each sub-agent its
own non-overlapping section of the plan, the existing issue list you
already fetched (don't have each sub-agent re-fetch it), and ask it to
report back the specific new issues it thinks are needed, not just a
general summary. For a small or simple plan, skip sub-agent delegation
and work through it directly; dispatching parallel sub-agents has a real
cost and isn't worth it for a handful of issues.

For each new issue you create:
1. Start the body with the `consal-plan-ref` marker for its section.
2. Follow it with a short, plain-language explanation of what the issue
   covers and why, written for a reader who doesn't read code, before
   any technical detail. This description is a claim about the work:
   keep it accurate to what you're actually asking for.
3. Use `gh issue create --repo {repo} --title "..." --body "..."`.

Only create new issues. Never close or edit an existing issue as part of
this task, even if the plan appears to have changed since it was filed:
that's a separate decision for a human to make.
"""
