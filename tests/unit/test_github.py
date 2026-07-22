import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from consal.github import (
    close_issue,
    comment_on_issue,
    create_issue,
    create_repo,
    list_open_issues,
)


@patch("consal.github.subprocess.run")
def test_list_open_issues_builds_expected_command(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="[]", stderr=""
    )
    list_open_issues("owner/repo")
    mock_run.assert_called_once_with(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            "owner/repo",
            "--state",
            "open",
            "--json",
            "number,title,body,url,state,labels,createdAt,updatedAt",
        ],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_list_open_issues_parses_json(mock_run: MagicMock) -> None:
    issues = [{"number": 1, "title": "fix the thing"}]
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=json.dumps(issues), stderr=""
    )
    assert list_open_issues("owner/repo") == issues


@patch("consal.github.subprocess.run")
def test_list_open_issues_propagates_gh_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        list_open_issues("owner/repo")


@patch("consal.github.subprocess.run")
def test_create_issue_builds_expected_command(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="https://github.com/owner/repo/issues/42\n", stderr=""
    )
    create_issue("owner/repo", "a title", "a body")
    mock_run.assert_called_once_with(
        ["gh", "issue", "create", "--repo", "owner/repo", "--title", "a title", "--body", "a body"],
        capture_output=True,
        text=True,
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_create_issue_parses_number_from_url(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="https://github.com/owner/repo/issues/42\n", stderr=""
    )
    result = create_issue("owner/repo", "a title", "a body")
    assert result == {"number": 42, "url": "https://github.com/owner/repo/issues/42"}


@patch("consal.github.subprocess.run")
def test_create_issue_propagates_gh_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        create_issue("owner/repo", "a title", "a body")


@patch("consal.github.subprocess.run")
def test_comment_on_issue_builds_expected_command(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    comment_on_issue("owner/repo", 42, "a comment")
    mock_run.assert_called_once_with(
        ["gh", "issue", "comment", "42", "--repo", "owner/repo", "--body", "a comment"],
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_comment_on_issue_propagates_gh_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        comment_on_issue("owner/repo", 42, "a comment")


@patch("consal.github.subprocess.run")
def test_close_issue_builds_expected_command_with_default_reason(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    close_issue("owner/repo", 42)
    mock_run.assert_called_once_with(
        ["gh", "issue", "close", "42", "--repo", "owner/repo", "--reason", "not planned"],
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_close_issue_accepts_explicit_reason(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    close_issue("owner/repo", 42, reason="completed")
    mock_run.assert_called_once_with(
        ["gh", "issue", "close", "42", "--repo", "owner/repo", "--reason", "completed"],
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_close_issue_propagates_gh_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        close_issue("owner/repo", 42)


@patch("consal.github.subprocess.run")
def test_create_repo_builds_expected_command(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    create_repo("owner/repo", Path("/workspace"))
    mock_run.assert_called_once_with(
        [
            "gh", "repo", "create", "owner/repo", "--private",
            "--source", "/workspace", "--remote", "origin", "--push",
        ],
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_create_repo_respects_visibility(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)
    create_repo("owner/repo", Path("/workspace"), visibility="public")
    mock_run.assert_called_once_with(
        [
            "gh", "repo", "create", "owner/repo", "--public",
            "--source", "/workspace", "--remote", "origin", "--push",
        ],
        check=True,
    )


@patch("consal.github.subprocess.run")
def test_create_repo_propagates_gh_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["gh"])
    with pytest.raises(subprocess.CalledProcessError):
        create_repo("owner/repo", Path("/workspace"))
