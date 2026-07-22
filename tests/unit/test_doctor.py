import socket
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from consal.doctor import (
    check_allowlist_reachability,
    check_environment,
    check_repo_access,
    check_subconfig,
    run,
)
from consal.settings import Settings


def _settings(tmp_path: Path, sub_config: str = "consal") -> Settings:
    return Settings(
        workspace=tmp_path, project_id="proj", repo="owner/repo", sub_config=sub_config
    )


@patch("consal.doctor.subprocess.run")
@patch("consal.doctor.shutil.which")
def test_check_environment_all_pass(mock_which: MagicMock, mock_run: MagicMock, monkeypatch) -> None:
    mock_which.return_value = "/usr/bin/whatever"
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
    monkeypatch.setenv("CONSAL_GH_PAT", "x")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "y")
    assert check_environment() is True


@patch("consal.doctor.subprocess.run")
@patch("consal.doctor.shutil.which")
def test_check_environment_fails_when_dco_missing(mock_which: MagicMock, mock_run: MagicMock, monkeypatch) -> None:
    mock_which.return_value = None
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
    monkeypatch.setenv("CONSAL_GH_PAT", "x")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "y")
    assert check_environment() is False


@patch("consal.doctor.subprocess.run")
@patch("consal.doctor.shutil.which")
def test_check_environment_fails_when_gh_unauthenticated(mock_which: MagicMock, mock_run: MagicMock, monkeypatch) -> None:
    mock_which.return_value = "/usr/bin/whatever"
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stderr="not logged in"
    )
    monkeypatch.setenv("CONSAL_GH_PAT", "x")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "y")
    assert check_environment() is False


@patch("consal.doctor.subprocess.run")
@patch("consal.doctor.shutil.which")
def test_check_environment_fails_when_token_env_vars_unset(
    mock_which: MagicMock, mock_run: MagicMock, monkeypatch
) -> None:
    mock_which.return_value = "/usr/bin/whatever"
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stderr="")
    monkeypatch.delenv("CONSAL_GH_PAT", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
    assert check_environment() is False


def test_check_subconfig_passes_for_valid_subconfig(tmp_path: Path) -> None:
    subconfig_dir = tmp_path / ".devcontainer" / "consal"
    subconfig_dir.mkdir(parents=True)
    (subconfig_dir / "Dockerfile").write_text("FROM scratch\n")
    (subconfig_dir / "guardrail-hook.sh").write_text("#!/bin/bash\n")
    (subconfig_dir / "allowlist.txt").write_text("api.anthropic.com\n")
    (subconfig_dir / "devcontainer.json").write_text('{"build": {"dockerfile": "Dockerfile"}}')

    assert check_subconfig(_settings(tmp_path)) is True


def test_check_subconfig_fails_and_reports_problems(tmp_path: Path, capsys) -> None:
    assert check_subconfig(_settings(tmp_path)) is False
    assert "missing devcontainer.json" in capsys.readouterr().out


@patch("consal.doctor.socket.getaddrinfo")
def test_check_allowlist_reachability_all_resolve(mock_getaddrinfo: MagicMock, tmp_path: Path) -> None:
    subconfig_dir = tmp_path / ".devcontainer" / "consal"
    subconfig_dir.mkdir(parents=True)
    (subconfig_dir / "allowlist.txt").write_text("# comment\napi.anthropic.com\ngithub.com\n")
    mock_getaddrinfo.return_value = [("fake",)]

    assert check_allowlist_reachability(_settings(tmp_path)) is True
    assert mock_getaddrinfo.call_count == 2


@patch("consal.doctor.socket.getaddrinfo")
def test_check_allowlist_reachability_fails_on_unresolvable_domain(
    mock_getaddrinfo: MagicMock, tmp_path: Path
) -> None:
    subconfig_dir = tmp_path / ".devcontainer" / "consal"
    subconfig_dir.mkdir(parents=True)
    (subconfig_dir / "allowlist.txt").write_text("nonexistent.invalid\n")
    mock_getaddrinfo.side_effect = socket.gaierror("not found")

    assert check_allowlist_reachability(_settings(tmp_path)) is False


def test_check_allowlist_reachability_empty_allowlist_passes(tmp_path: Path) -> None:
    subconfig_dir = tmp_path / ".devcontainer" / "consal"
    subconfig_dir.mkdir(parents=True)
    (subconfig_dir / "allowlist.txt").write_text("# just comments\n\n")

    assert check_allowlist_reachability(_settings(tmp_path)) is True


def test_check_allowlist_reachability_fails_when_file_missing(tmp_path: Path) -> None:
    assert check_allowlist_reachability(_settings(tmp_path)) is False


def test_check_repo_access_fails_when_pat_unset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CONSAL_GH_PAT", raising=False)
    assert check_repo_access(_settings(tmp_path)) is False


@patch("consal.doctor.subprocess.run")
def test_check_repo_access_fails_on_gh_error(mock_run: MagicMock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONSAL_GH_PAT", "scoped-pat")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="not found"
    )
    assert check_repo_access(_settings(tmp_path)) is False


@patch("consal.doctor.subprocess.run")
def test_check_repo_access_fails_on_read_only_permission(mock_run: MagicMock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONSAL_GH_PAT", "scoped-pat")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"viewerPermission": "READ"}', stderr=""
    )
    assert check_repo_access(_settings(tmp_path)) is False


@patch("consal.doctor.subprocess.run")
def test_check_repo_access_passes_on_write_permission(mock_run: MagicMock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONSAL_GH_PAT", "scoped-pat")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"viewerPermission": "WRITE"}', stderr=""
    )
    assert check_repo_access(_settings(tmp_path)) is True


@patch("consal.doctor.subprocess.run")
def test_check_repo_access_uses_pat_not_ambient_env(mock_run: MagicMock, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CONSAL_GH_PAT", "scoped-pat")
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"viewerPermission": "WRITE"}', stderr=""
    )
    check_repo_access(_settings(tmp_path))
    assert mock_run.call_args.kwargs["env"]["GH_TOKEN"] == "scoped-pat"


@patch("consal.doctor.check_repo_access", return_value=True)
@patch("consal.doctor.check_allowlist_reachability", return_value=True)
@patch("consal.doctor.check_subconfig", return_value=True)
@patch("consal.doctor.check_environment", return_value=True)
def test_run_returns_zero_when_all_pass(
    mock_env: MagicMock, mock_sub: MagicMock, mock_allow: MagicMock, mock_repo: MagicMock, tmp_path: Path
) -> None:
    assert run(_settings(tmp_path)) == 0


@patch("consal.doctor.check_repo_access", return_value=True)
@patch("consal.doctor.check_allowlist_reachability", return_value=True)
@patch("consal.doctor.check_subconfig", return_value=True)
@patch("consal.doctor.check_environment", return_value=False)
def test_run_returns_nonzero_when_any_check_fails(
    mock_env: MagicMock, mock_sub: MagicMock, mock_allow: MagicMock, mock_repo: MagicMock, tmp_path: Path
) -> None:
    assert run(_settings(tmp_path)) == 1
