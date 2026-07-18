"""Tests the real guardrail hook script as a subprocess, not a Python
reimplementation of its rules. A Claude Code PreToolUse hook has to be a
shell command; a parallel Python policy checker would never run in the
actual enforcement path, so there's nothing to unit test except the real
artifact (lesson #6, CONSAL_GOALS.md: mocked infra that never exercises
the real underlying tool misses exactly the bugs that matter). Needs only
bash + jq, both present in this sandbox, so this runs as a fast unit test
despite shelling out to a real subprocess.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[2] / "src" / "consal" / "templates" / "guardrail-hook.sh"


def run_hook(tool_name: str, command: str | None = None, cwd: str = "/workspace") -> subprocess.CompletedProcess:
    tool_input: dict = {}
    if command is not None:
        tool_input["command"] = command
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input, "cwd": cwd})
    return subprocess.run(
        ["bash", str(HOOK)], input=payload, capture_output=True, text=True
    )


def test_hook_is_executable() -> None:
    assert HOOK.is_file()


def test_ignores_non_bash_tools() -> None:
    result = run_hook("Read", None)
    assert result.returncode == 0


def test_ignores_empty_command() -> None:
    result = run_hook("Bash", "")
    assert result.returncode == 0


def test_allows_ordinary_push_to_feature_branch() -> None:
    result = run_hook("Bash", "git push origin my-feature-branch")
    assert result.returncode == 0


def test_allows_ordinary_gh_commands() -> None:
    result = run_hook("Bash", "gh pr create --title x --body y")
    assert result.returncode == 0


def test_blocks_force_push() -> None:
    result = run_hook("Bash", "git push --force origin my-branch")
    assert result.returncode == 2
    assert "force" in result.stderr.lower()


def test_blocks_force_with_lease() -> None:
    result = run_hook("Bash", "git push --force-with-lease origin my-branch")
    assert result.returncode == 2


def test_blocks_short_force_flag() -> None:
    result = run_hook("Bash", "git push -f origin my-branch")
    assert result.returncode == 2


def test_blocks_explicit_push_to_main() -> None:
    result = run_hook("Bash", "git push origin main")
    assert result.returncode == 2
    assert "main" in result.stderr.lower()


def test_blocks_explicit_push_to_master() -> None:
    result = run_hook("Bash", "git push origin master")
    assert result.returncode == 2


def _init_repo_with_commit(repo: Path, branch: str) -> None:
    # git rev-parse --abbrev-ref HEAD fails (falls back to the literal
    # string "HEAD") on an unborn branch with zero commits, verified
    # directly rather than assumed. A real Consal-managed project always
    # has at least one commit before autonomous work starts, so this
    # fixture matches realistic state rather than an edge case the hook
    # isn't meant to cover (it's a backstop, not the primary mechanism;
    # GitHub branch protection is).
    subprocess.run(["git", "init", "-b", branch, str(repo)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
        check=True,
        capture_output=True,
    )


def test_blocks_bare_push_while_on_main(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo_with_commit(repo, "main")
    result = run_hook("Bash", "git push", cwd=str(repo))
    assert result.returncode == 2
    assert "main" in result.stderr.lower()


def test_allows_bare_push_while_on_feature_branch(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo_with_commit(repo, "my-feature")
    result = run_hook("Bash", "git push", cwd=str(repo))
    assert result.returncode == 0


def test_blocks_gh_pr_merge() -> None:
    result = run_hook("Bash", "gh pr merge 42 --squash")
    assert result.returncode == 2
    assert "merge" in result.stderr.lower()


def test_blocks_gh_repo_edit() -> None:
    result = run_hook("Bash", "gh repo edit --enable-issues=false")
    assert result.returncode == 2


def test_blocks_branch_protection_api() -> None:
    result = run_hook(
        "Bash", "gh api -X PUT repos/org/repo/branches/main/protection"
    )
    assert result.returncode == 2
    assert "protection" in result.stderr.lower()


def test_blocks_gh_secret_set() -> None:
    result = run_hook("Bash", "gh secret set MY_SECRET --body x")
    assert result.returncode == 2


def test_malformed_input_fails_open() -> None:
    result = subprocess.run(
        ["bash", str(HOOK)], input="not json", capture_output=True, text=True
    )
    assert result.returncode == 0
