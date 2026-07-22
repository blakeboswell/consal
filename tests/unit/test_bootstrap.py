import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from consal.bootstrap import create_project, detect_origin_repo


def _no_remote(*args, **kwargs):
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="fatal: No such remote")


def _remote(url: str):
    def _run(*args, **kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=f"{url}\n", stderr="")
    return _run


@patch("consal.bootstrap.github.create_repo")
@patch("consal.bootstrap.subprocess.run")
def test_create_project_inits_git_when_not_a_repo(
    mock_run: MagicMock, mock_create_repo: MagicMock, tmp_path: Path
) -> None:
    mock_run.side_effect = _no_remote
    create_project(tmp_path, "consal", "owner/repo")

    argvs = [call.args[0] for call in mock_run.call_args_list]
    assert ["git", "init"] in argvs
    assert (tmp_path / ".devcontainer" / "consal" / "devcontainer.json").is_file()
    mock_create_repo.assert_called_once_with("owner/repo", tmp_path, "private")


@patch("consal.bootstrap.github.create_repo")
@patch("consal.bootstrap.subprocess.run")
def test_create_project_skips_git_init_when_already_a_repo(
    mock_run: MagicMock, mock_create_repo: MagicMock, tmp_path: Path
) -> None:
    (tmp_path / ".git").mkdir()
    mock_run.side_effect = _no_remote
    create_project(tmp_path, "consal", "owner/repo")

    argvs = [call.args[0] for call in mock_run.call_args_list]
    assert ["git", "init"] not in argvs


@patch("consal.bootstrap.github.create_repo")
@patch("consal.bootstrap.subprocess.run")
def test_create_project_raises_when_origin_remote_already_exists(
    mock_run: MagicMock, mock_create_repo: MagicMock, tmp_path: Path
) -> None:
    mock_run.side_effect = _remote("https://github.com/existing/repo.git")
    with pytest.raises(RuntimeError, match="already has an 'origin' remote"):
        create_project(tmp_path, "consal", "owner/repo")

    mock_create_repo.assert_not_called()
    assert not (tmp_path / ".devcontainer").exists()


@patch("consal.bootstrap.github.create_repo")
@patch("consal.bootstrap.subprocess.run")
def test_create_project_commits_only_generated_paths(
    mock_run: MagicMock, mock_create_repo: MagicMock, tmp_path: Path
) -> None:
    (tmp_path / "unrelated.txt").write_text("do not touch")
    mock_run.side_effect = _no_remote
    create_project(tmp_path, "consal", "owner/repo")

    add_calls = [call.args[0] for call in mock_run.call_args_list if call.args[0][:2] == ["git", "add"]]
    assert len(add_calls) == 1
    added_paths = add_calls[0][2:]
    assert str(Path(".devcontainer") / "consal") in added_paths
    assert str(Path(".claude") / "settings.json") in added_paths
    assert "unrelated.txt" not in added_paths

    commit_calls = [call.args[0] for call in mock_run.call_args_list if call.args[0][:2] == ["git", "commit"]]
    assert len(commit_calls) == 1


def test_detect_origin_repo_parses_https_url(tmp_path: Path) -> None:
    with patch("consal.bootstrap.subprocess.run", side_effect=_remote("https://github.com/owner/repo.git")):
        assert detect_origin_repo(tmp_path) == "owner/repo"


def test_detect_origin_repo_parses_ssh_url(tmp_path: Path) -> None:
    with patch("consal.bootstrap.subprocess.run", side_effect=_remote("git@github.com:owner/repo.git")):
        assert detect_origin_repo(tmp_path) == "owner/repo"


def test_detect_origin_repo_returns_none_when_no_remote(tmp_path: Path) -> None:
    with patch("consal.bootstrap.subprocess.run", side_effect=_no_remote):
        assert detect_origin_repo(tmp_path) is None
