from consal.prompts import prompt_for_decomposition, prompt_for_issue


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


def test_decomposition_includes_repo_and_plan_text() -> None:
    prompt = prompt_for_decomposition("owner/repo", "## Component A\nDo the thing.")
    assert "owner/repo" in prompt
    assert "## Component A\nDo the thing." in prompt


def test_decomposition_instructs_checking_existing_issues_first() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan").lower()
    assert "gh issue list" in prompt
    assert "existing issue" in prompt


def test_decomposition_instructs_the_idempotency_marker() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan")
    assert "consal-plan-ref" in prompt


def test_decomposition_instructs_plain_language_explanation() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan").lower()
    assert "plain-language" in prompt


def test_decomposition_instructs_effort_scaling_for_sub_agents() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan").lower()
    assert "sub-agent" in prompt
    assert "skip sub-agent delegation" in prompt


def test_decomposition_instructs_never_closing_or_editing_issues() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan").lower()
    assert "never close or edit" in prompt


def test_decomposition_uses_gh_issue_create() -> None:
    prompt = prompt_for_decomposition("owner/repo", "a plan")
    assert "gh issue create" in prompt
