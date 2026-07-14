"""Local guardrail checks — defense in depth, never the sole backstop.

GitHub's own branch protection is the real backstop (EIGEN_GOALS.md,
"Isolation & safety goals"). This module exists to catch the agent
attempting a force-push, a direct push to a protected branch, or a change
to branch/repo protection settings *before* it reaches GitHub — not to
replace GitHub-side protection.
"""

from __future__ import annotations


class GuardrailViolation(Exception):
    """Raised when a proposed action would violate a guardrail."""


def check_git_command(argv: list[str]) -> None:
    """Raise GuardrailViolation if ``argv`` is a disallowed git operation.

    Not yet implemented.
    """
    raise NotImplementedError
