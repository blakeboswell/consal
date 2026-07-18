from pathlib import Path
from unittest.mock import MagicMock, patch

from consal.container import TurnResult
from consal.scheduler import TickResult, next_turn, run_loop_once

FAKE_STATE_DIR = Path("/fake/state/dir")


def _issue(number: int, created_at: str, title: str = "t", body: str = "b") -> dict:
    return {"number": number, "title": title, "body": body, "createdAt": created_at}


@patch("consal.scheduler.github.list_open_issues")
def test_next_turn_returns_none_when_no_open_issues(mock_list: MagicMock) -> None:
    mock_list.return_value = []
    assert next_turn("owner/repo", None) is None


@patch("consal.scheduler.github.list_open_issues")
def test_next_turn_picks_oldest_issue_when_none_active(mock_list: MagicMock) -> None:
    mock_list.return_value = [
        _issue(2, "2024-01-02T00:00:00Z"),
        _issue(1, "2024-01-01T00:00:00Z"),
        _issue(3, "2024-01-03T00:00:00Z"),
    ]
    result = next_turn("owner/repo", None)
    assert result["number"] == 1


@patch("consal.scheduler.github.list_open_issues")
def test_next_turn_sticks_with_active_issue_if_still_open(mock_list: MagicMock) -> None:
    mock_list.return_value = [
        _issue(1, "2024-01-01T00:00:00Z"),
        _issue(2, "2024-01-02T00:00:00Z"),
    ]
    result = next_turn("owner/repo", active_issue_number=2)
    assert result["number"] == 2


@patch("consal.scheduler.github.list_open_issues")
def test_next_turn_picks_new_issue_once_active_one_closed(mock_list: MagicMock) -> None:
    # active issue 99 no longer appears in the open list: it closed
    mock_list.return_value = [_issue(5, "2024-01-01T00:00:00Z")]
    result = next_turn("owner/repo", active_issue_number=99)
    assert result["number"] == 5


@patch("consal.scheduler.state.state_dir", return_value=FAKE_STATE_DIR)
@patch("consal.scheduler.container.ensure_container_up")
@patch("consal.scheduler.state.read_active_issue")
@patch("consal.scheduler.state.write_active_issue")
@patch("consal.scheduler.github.list_open_issues")
def test_run_loop_once_returns_idle_tick_when_no_issues(
    mock_list: MagicMock,
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_ensure_up: MagicMock,
    mock_state_dir: MagicMock,
) -> None:
    mock_read.return_value = None
    mock_list.return_value = []

    result = run_loop_once("proj", Path("/workspace"), "owner/repo", "consal")

    assert result == TickResult(issue_number=None, turn=None)
    assert result.was_idle is True
    mock_ensure_up.assert_called_once_with(Path("/workspace"), "consal")


@patch("consal.scheduler.state.state_dir", return_value=FAKE_STATE_DIR)
@patch("consal.scheduler.container.ensure_container_up")
@patch("consal.scheduler.container.run_turn")
@patch("consal.scheduler.state.read_active_issue")
@patch("consal.scheduler.state.write_active_issue")
@patch("consal.scheduler.github.list_open_issues")
@patch("consal.scheduler.github.comment_on_issue")
def test_run_loop_once_dispatches_turn_and_records_success(
    mock_comment: MagicMock,
    mock_list: MagicMock,
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_run_turn: MagicMock,
    mock_ensure_up: MagicMock,
    mock_state_dir: MagicMock,
) -> None:
    mock_read.return_value = None
    mock_list.return_value = [_issue(7, "2024-01-01T00:00:00Z", title="Fix X", body="Do Y")]
    mock_run_turn.return_value = TurnResult(exit_code=0, stdout="done", stderr="")

    result = run_loop_once("proj", Path("/workspace"), "owner/repo", "consal")

    assert result.issue_number == 7
    assert result.was_idle is False
    assert result.turn.succeeded is True
    mock_write.assert_called_once_with(FAKE_STATE_DIR, 7)
    mock_run_turn.assert_called_once()
    turn_args = mock_run_turn.call_args[0]
    assert turn_args[0] == Path("/workspace")
    assert turn_args[1] == "consal"
    assert "Fix X" in turn_args[2]
    assert "Do Y" in turn_args[2]
    mock_comment.assert_not_called()


@patch("consal.scheduler.state.state_dir", return_value=FAKE_STATE_DIR)
@patch("consal.scheduler.container.ensure_container_up")
@patch("consal.scheduler.container.run_turn")
@patch("consal.scheduler.state.read_active_issue")
@patch("consal.scheduler.state.write_active_issue")
@patch("consal.scheduler.github.list_open_issues")
@patch("consal.scheduler.github.comment_on_issue")
def test_run_loop_once_comments_on_issue_when_turn_fails(
    mock_comment: MagicMock,
    mock_list: MagicMock,
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_run_turn: MagicMock,
    mock_ensure_up: MagicMock,
    mock_state_dir: MagicMock,
) -> None:
    mock_read.return_value = None
    mock_list.return_value = [_issue(9, "2024-01-01T00:00:00Z")]
    mock_run_turn.return_value = TurnResult(exit_code=1, stdout="", stderr="boom")

    result = run_loop_once("proj", Path("/workspace"), "owner/repo", "consal")

    assert result.turn.succeeded is False
    mock_comment.assert_called_once_with(
        "owner/repo", 9, mock_comment.call_args[0][2]
    )
    assert "boom" in mock_comment.call_args[0][2]


@patch("consal.scheduler.state.state_dir", return_value=FAKE_STATE_DIR)
@patch("consal.scheduler.container.ensure_container_up")
@patch("consal.scheduler.state.read_active_issue")
@patch("consal.scheduler.state.write_active_issue")
@patch("consal.scheduler.github.list_open_issues")
def test_run_loop_once_clears_active_issue_state_when_idle(
    mock_list: MagicMock,
    mock_write: MagicMock,
    mock_read: MagicMock,
    mock_ensure_up: MagicMock,
    mock_state_dir: MagicMock,
) -> None:
    mock_read.return_value = 3
    mock_list.return_value = []

    run_loop_once("proj", Path("/workspace"), "owner/repo", "consal")

    mock_write.assert_called_once_with(FAKE_STATE_DIR, None)
