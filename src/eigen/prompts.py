"""Prompt construction for autonomous turns.

Kept separate from `scheduler.py` so prompt wording can change without
touching dispatch/control-flow logic, and so it's independently unit
testable.
"""

from __future__ import annotations


def prompt_for_issue(repo: str, issue_number: int, issue_title: str, issue_body: str) -> str:
    """Build the prompt handed to `claude -p` for working a given issue.

    Doesn't repeat the guardrail hook's rules — force-push, direct push to
    main/master, `gh pr merge`, etc. are already enforced at the tool-call
    level regardless of what this prompt says (EIGEN_GOALS.md's isolation
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
3. Do not merge the pull request yourself — a human reviews and merges.

If the issue is unclear or you get stuck, leave a comment on issue
#{issue_number} explaining what's blocking you, rather than guessing.
"""
