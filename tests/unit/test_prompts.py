from consal.prompts import prompt_for_issue


def test_includes_repo_and_issue_number() -> None:
    prompt = prompt_for_issue("owner/repo", 42, "Fix the thing", "Some body text")
    assert "owner/repo" in prompt
    assert "42" in prompt


def test_includes_issue_title_and_body() -> None:
    prompt = prompt_for_issue("owner/repo", 42, "Fix the thing", "Some body text")
    assert "Fix the thing" in prompt
    assert "Some body text" in prompt


def test_instructs_working_on_a_new_branch_not_main() -> None:
    prompt = prompt_for_issue("owner/repo", 1, "t", "b").lower()
    assert "branch" in prompt
    assert "main" in prompt or "master" in prompt


def test_instructs_opening_a_pr_without_merging_it() -> None:
    prompt = prompt_for_issue("owner/repo", 1, "t", "b").lower()
    assert "pull request" in prompt
    assert "do not merge" in prompt


def test_instructs_commenting_if_stuck_rather_than_guessing() -> None:
    prompt = prompt_for_issue("owner/repo", 1, "t", "b").lower()
    assert "comment" in prompt


def test_handles_empty_body_without_raising() -> None:
    prompt = prompt_for_issue("owner/repo", 1, "a title", "")
    assert "owner/repo" in prompt
    assert "a title" in prompt
