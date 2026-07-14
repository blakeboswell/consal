import json
from pathlib import Path

from eigen.config import validate_subconfig


def test_validate_subconfig_missing_devcontainer_json(tmp_path: Path) -> None:
    problems = validate_subconfig(tmp_path)
    assert problems == [f"missing devcontainer.json in {tmp_path}"]


def test_validate_subconfig_ok(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    assert validate_subconfig(tmp_path) == []


def test_validate_subconfig_missing_dockerfile(tmp_path: Path) -> None:
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    problems = validate_subconfig(tmp_path)
    assert len(problems) == 1
    assert "referenced dockerfile not found" in problems[0]


def test_validate_subconfig_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "devcontainer.json").write_text("{not valid json")
    problems = validate_subconfig(tmp_path)
    assert len(problems) == 1
    assert "not valid JSON" in problems[0]


def test_validate_subconfig_eigen_test_fixture() -> None:
    """The real `.devcontainer/eigen-test/` fixture used by
    tests/integration/test_container.py — checked for real, not just
    synthetic tmp_path fixtures, so a broken reference in it is caught
    here rather than only surfacing during a live `dco` run on the host.
    """
    repo_root = Path(__file__).resolve().parents[2]
    fixture_dir = repo_root / ".devcontainer" / "eigen-test"
    assert validate_subconfig(fixture_dir) == []
