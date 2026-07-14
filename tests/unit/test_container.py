import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eigen.container import TurnResult, ensure_container_up, exec_in_container, run_turn


def test_turn_result_succeeded_true_on_zero_exit() -> None:
    assert TurnResult(exit_code=0, stdout="", stderr="").succeeded is True


def test_turn_result_succeeded_false_on_nonzero_exit() -> None:
    assert TurnResult(exit_code=1, stdout="", stderr="boom").succeeded is False


@patch("eigen.container.subprocess.run")
def test_ensure_container_up_invokes_dco_sub_config(mock_run: MagicMock) -> None:
    ensure_container_up(Path("/workspace"), "eigen")
    mock_run.assert_called_once_with(
        ["dco", "/workspace", "--sub-config", "eigen", "--up-only"], check=True
    )


@patch("eigen.container.subprocess.run")
def test_ensure_container_up_propagates_dco_failure(mock_run: MagicMock) -> None:
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd=["dco"])
    with pytest.raises(subprocess.CalledProcessError):
        ensure_container_up(Path("/workspace"), "eigen")


@patch("eigen.container.subprocess.run")
def test_run_turn_builds_expected_command(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="ok", stderr=""
    )
    run_turn(Path("/workspace"), "eigen", "implement issue #42")
    mock_run.assert_called_once_with(
        [
            "devcontainer",
            "exec",
            "--workspace-folder",
            "/workspace",
            "--config",
            "/workspace/.devcontainer/eigen/devcontainer.json",
            "--",
            "claude",
            "-p",
            "implement issue #42",
        ],
        input=None,
        capture_output=True,
        text=True,
    )


@patch("eigen.container.subprocess.run")
def test_exec_in_container_passes_input_through(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=2, stdout="", stderr="blocked"
    )
    result = exec_in_container(
        Path("/workspace"), "eigen", ["bash", "hook.sh"], input="payload"
    )
    mock_run.assert_called_once_with(
        [
            "devcontainer",
            "exec",
            "--workspace-folder",
            "/workspace",
            "--config",
            "/workspace/.devcontainer/eigen/devcontainer.json",
            "--",
            "bash",
            "hook.sh",
        ],
        input="payload",
        capture_output=True,
        text=True,
    )
    assert result == TurnResult(exit_code=2, stdout="", stderr="blocked")


@patch("eigen.container.subprocess.run")
def test_run_turn_returns_result_on_success(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="done", stderr=""
    )
    result = run_turn(Path("/workspace"), "eigen", "prompt")
    assert result == TurnResult(exit_code=0, stdout="done", stderr="")
    assert result.succeeded is True


@patch("eigen.container.subprocess.run")
def test_run_turn_returns_result_on_failure_without_raising(mock_run: MagicMock) -> None:
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="claude crashed"
    )
    result = run_turn(Path("/workspace"), "eigen", "prompt")
    assert result == TurnResult(exit_code=1, stdout="", stderr="claude crashed")
    assert result.succeeded is False
