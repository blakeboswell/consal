from pathlib import Path
from unittest.mock import MagicMock, patch

from consal.cli import main
from consal.container import TurnResult
from consal.scheduler import TickResult
from consal.settings import load_config_file


@patch("consal.cli.doctor_module.run")
def test_doctor_dispatches_with_resolved_settings(mock_doctor_run: MagicMock, tmp_path: Path) -> None:
    mock_doctor_run.return_value = 0
    exit_code = main(
        [
            "doctor",
            "--workspace",
            str(tmp_path),
            "--project-id",
            "proj",
            "--repo",
            "owner/repo",
        ]
    )
    assert exit_code == 0
    mock_doctor_run.assert_called_once()
    settings = mock_doctor_run.call_args[0][0]
    assert settings.project_id == "proj"
    assert settings.repo == "owner/repo"
    assert settings.sub_config == "consal"


@patch("consal.cli.doctor_module.run")
def test_doctor_propagates_nonzero_exit(mock_doctor_run: MagicMock, tmp_path: Path) -> None:
    mock_doctor_run.return_value = 1
    exit_code = main(
        ["doctor", "--workspace", str(tmp_path), "--project-id", "p", "--repo", "o/r"]
    )
    assert exit_code == 1


def test_missing_required_settings_errors_cleanly(tmp_path: Path, capsys) -> None:
    exit_code = main(["doctor", "--workspace", str(tmp_path)])
    assert exit_code == 1
    assert "missing required setting" in capsys.readouterr().err


@patch("consal.cli.run_loop_once")
def test_run_reports_idle(mock_run_loop_once: MagicMock, tmp_path: Path, capsys) -> None:
    mock_run_loop_once.return_value = TickResult(issue_number=None, turn=None)
    exit_code = main(
        ["run", "--workspace", str(tmp_path), "--project-id", "p", "--repo", "o/r"]
    )
    assert exit_code == 0
    assert "idle" in capsys.readouterr().out.lower()


@patch("consal.cli.run_loop_once")
def test_run_reports_success(mock_run_loop_once: MagicMock, tmp_path: Path, capsys) -> None:
    mock_run_loop_once.return_value = TickResult(
        issue_number=7, turn=TurnResult(exit_code=0, stdout="", stderr="")
    )
    exit_code = main(
        ["run", "--workspace", str(tmp_path), "--project-id", "p", "--repo", "o/r"]
    )
    assert exit_code == 0
    assert "#7" in capsys.readouterr().out


@patch("consal.cli.run_loop_once")
def test_run_reports_failure_with_nonzero_exit(mock_run_loop_once: MagicMock, tmp_path: Path, capsys) -> None:
    mock_run_loop_once.return_value = TickResult(
        issue_number=9, turn=TurnResult(exit_code=1, stdout="", stderr="boom")
    )
    exit_code = main(
        ["run", "--workspace", str(tmp_path), "--project-id", "p", "--repo", "o/r"]
    )
    assert exit_code == 1
    assert "#9" in capsys.readouterr().err


@patch("consal.cli.run_loop_once")
def test_run_passes_resolved_settings_through(mock_run_loop_once: MagicMock, tmp_path: Path) -> None:
    mock_run_loop_once.return_value = TickResult(issue_number=None, turn=None)
    main(
        [
            "run",
            "--workspace",
            str(tmp_path),
            "--project-id",
            "myproj",
            "--repo",
            "owner/repo",
            "--sub-config",
            "custom",
        ]
    )
    mock_run_loop_once.assert_called_once_with("myproj", tmp_path.resolve(), "owner/repo", "custom")


# init runs the real config.generate_subconfig/write_config_file (no
# mocking). Both are fast, pure filesystem operations against tmp_path,
# no subprocess/network involved, so there's no cost to exercising the
# real wiring instead of asserting on mocked call shapes.


def test_init_generates_subconfig_with_default_name(tmp_path: Path, capsys) -> None:
    exit_code = main(["init", "--workspace", str(tmp_path)])
    assert exit_code == 0
    subconfig_dir = tmp_path / ".devcontainer" / "consal"
    assert (subconfig_dir / "devcontainer.json").is_file()
    assert (subconfig_dir / "guardrail-hook.sh").is_file()
    assert (subconfig_dir / "allowlist.txt").is_file()
    assert "generated sub-config" in capsys.readouterr().out


def test_init_writes_config_file_with_sub_config_default(tmp_path: Path) -> None:
    main(["init", "--workspace", str(tmp_path)])
    assert load_config_file(tmp_path) == {"sub_config": "consal"}


def test_init_records_project_id_and_repo_when_given(tmp_path: Path) -> None:
    main(
        [
            "init",
            "--workspace",
            str(tmp_path),
            "--project-id",
            "myproj",
            "--repo",
            "owner/repo",
        ]
    )
    assert load_config_file(tmp_path) == {
        "sub_config": "consal",
        "project_id": "myproj",
        "repo": "owner/repo",
    }


def test_init_respects_custom_sub_config_name(tmp_path: Path) -> None:
    main(["init", "--workspace", str(tmp_path), "--sub-config", "custom"])
    assert (tmp_path / ".devcontainer" / "custom" / "devcontainer.json").is_file()
    assert load_config_file(tmp_path) == {"sub_config": "custom"}


def test_init_does_not_require_project_id_or_repo(tmp_path: Path) -> None:
    # unlike doctor/run, init must not go through resolve_settings's
    # required-field check, since generating a sub-config needs neither.
    exit_code = main(["init", "--workspace", str(tmp_path)])
    assert exit_code == 0


def test_init_merges_into_existing_config_without_clobbering(tmp_path: Path) -> None:
    main(["init", "--workspace", str(tmp_path), "--project-id", "p", "--repo", "o/r"])
    main(["init", "--workspace", str(tmp_path), "--sub-config", "custom"])
    assert load_config_file(tmp_path) == {
        "project_id": "p",
        "repo": "o/r",
        "sub_config": "custom",
    }
