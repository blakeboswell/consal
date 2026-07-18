#!/bin/bash
# PreToolUse hook (Bash matcher) for Consal-managed autonomous sessions.
#
# Hard-blocks the handful of git/gh operations that are never legitimate
# under Consal's PR-only autonomous workflow (see CONSAL_GOALS.md,
# "Isolation & safety goals" -- a human is the only one who can merge
# code or touch branch/repo protection). This fires even under
# --dangerously-skip-permissions: hooks are a separate enforcement layer
# from the permission system.
#
# Deliberately narrow and a backstop, not the primary safety mechanism --
# GitHub's own branch protection is that (CONSAL_GOALS.md: "the local
# layer never treated as sufficient on its own"). Does not block all
# pushes or all CI-workflow-file edits; the PR-review checkpoint covers
# those.
#
# Blocks via exit code 2 (stderr becomes Claude's feedback). Malformed
# input fails open (exit 0) rather than blocking legitimate work on a
# parse error.
#
# This policy is autonomy-specific, so it's authored and owned here in
# Consal, not in dco -- dco stays generic (see CONSAL_GOALS.md's
# architecture rationale). config.generate_subconfig copies this file
# as-is into each managed project's sub-config directory.

INPUT="$(cat)"

TOOL_NAME="$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || true)"
[[ "$TOOL_NAME" == "Bash" ]] || exit 0

COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)"
[[ -n "$COMMAND" ]] || exit 0

PROJECT_DIR="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)"
PROJECT_DIR="${PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-/workspace}}"

block() {
  echo "consal guardrail: blocked — $1" >&2
  exit 2
}

# git push --force / -f / --force-with-lease, anywhere in the command
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])git[[:space:]]+push([[:space:]].*)?[[:space:]](--force(-with-lease)?|-f)([[:space:]]|$)'; then
  block "git push --force is never allowed; add corrective commits instead of rewriting history."
fi

# git push explicitly naming main/master as the target branch
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])git[[:space:]]+push([[:space:]]+[^|;&]*)?[[:space:]](refs/heads/)?(main|master)([[:space:]]|$)'; then
  block "direct push to main/master is never allowed; open a PR instead."
fi

# bare `git push` (no explicit remote/branch) while checked out on main/master
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])git[[:space:]]+push([[:space:]]+-[-a-zA-Z]*)*[[:space:]]*$'; then
  CURRENT_BRANCH="$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    block "current branch is $CURRENT_BRANCH; direct push to main/master is never allowed, open a PR instead."
  fi
fi

# gh pr merge — a human always merges
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$)'; then
  block "gh pr merge is never allowed; a human always merges."
fi

# gh repo edit — repo settings are out of scope
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])gh[[:space:]]+repo[[:space:]]+edit([[:space:]]|$)'; then
  block "gh repo edit is never allowed; repo settings are out of scope."
fi

# gh api against branch-protection endpoints
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])gh[[:space:]]+api([[:space:]]|$).*branches/[^[:space:]]*/protection'; then
  block "modifying branch protection via gh api is never allowed."
fi

# gh secret set — credential/secret management is out of scope
if echo "$COMMAND" | grep -Eq '(^|[[:space:]])gh[[:space:]]+secret[[:space:]]+set([[:space:]]|$)'; then
  block "gh secret set is never allowed."
fi

exit 0
