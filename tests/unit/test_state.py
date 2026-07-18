from pathlib import Path
from unittest.mock import patch

import pytest

from eigen.state import read_active_issue, state_dir, write_active_issue


def test_state_dir_is_under_home_and_project_id() -> None:
    with patch("eigen.state.Path.home", return_value=Path("/home/testuser")):
        assert state_dir("my-project") == Path("/home/testuser/.eigen/my-project")


def test_read_active_issue_returns_none_when_no_file(tmp_path: Path) -> None:
    assert read_active_issue(tmp_path) is None


def test_write_then_read_active_issue(tmp_path: Path) -> None:
    write_active_issue(tmp_path, 42)
    assert read_active_issue(tmp_path) == 42


def test_write_active_issue_creates_state_dir_if_missing(tmp_path: Path) -> None:
    nested = tmp_path / "does" / "not" / "exist" / "yet"
    write_active_issue(nested, 7)
    assert read_active_issue(nested) == 7


def test_write_none_clears_active_issue(tmp_path: Path) -> None:
    write_active_issue(tmp_path, 42)
    write_active_issue(tmp_path, None)
    assert read_active_issue(tmp_path) is None


def test_write_none_is_a_no_op_when_nothing_was_set(tmp_path: Path) -> None:
    write_active_issue(tmp_path, None)
    assert read_active_issue(tmp_path) is None


def test_read_active_issue_raises_on_corrupted_state_file(tmp_path: Path) -> None:
    (tmp_path / "active_issue").write_text("not-a-number")
    with pytest.raises(ValueError):
        read_active_issue(tmp_path)


def test_write_active_issue_overwrites_previous_value(tmp_path: Path) -> None:
    write_active_issue(tmp_path, 1)
    write_active_issue(tmp_path, 2)
    assert read_active_issue(tmp_path) == 2
