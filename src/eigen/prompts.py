"""Prompt construction for autonomous turns.

Kept separate from `scheduler.py` so prompt wording can change without
touching dispatch/control-flow logic, and so it's independently unit
testable.
"""

from __future__ import annotations


def prompt_for_issue(repo: str, issue_number: int, issue_title: str, issue_body: str) -> str:
    """Build the prompt handed to `claude -p` for working a given issue.

    Not yet implemented.
    """
    raise NotImplementedError
