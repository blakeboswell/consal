import json
from pathlib import Path

from consal.config import generate_subconfig, validate_subconfig


def test_validate_subconfig_missing_devcontainer_json(tmp_path: Path) -> None:
    problems = validate_subconfig(tmp_path)
    assert problems == [f"missing devcontainer.json in {tmp_path}"]


def test_validate_subconfig_ok(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "guardrail-hook.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "allowlist.txt").write_text("api.anthropic.com\n")
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    assert validate_subconfig(tmp_path) == []


def test_validate_subconfig_missing_dockerfile(tmp_path: Path) -> None:
    (tmp_path / "guardrail-hook.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "allowlist.txt").write_text("api.anthropic.com\n")
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    problems = validate_subconfig(tmp_path)
    assert len(problems) == 1
    assert "referenced dockerfile not found" in problems[0]


def test_validate_subconfig_missing_guardrail_hook(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "allowlist.txt").write_text("api.anthropic.com\n")
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    problems = validate_subconfig(tmp_path)
    assert problems == [f"missing guardrail-hook.sh in {tmp_path}"]


def test_validate_subconfig_missing_allowlist(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM scratch\n")
    (tmp_path / "guardrail-hook.sh").write_text("#!/bin/bash\nexit 0\n")
    (tmp_path / "devcontainer.json").write_text(
        json.dumps({"build": {"dockerfile": "Dockerfile"}})
    )
    problems = validate_subconfig(tmp_path)
    assert problems == [f"missing allowlist.txt in {tmp_path}"]


def test_validate_subconfig_invalid_json(tmp_path: Path) -> None:
    (tmp_path / "devcontainer.json").write_text("{not valid json")
    problems = validate_subconfig(tmp_path)
    assert len(problems) == 1
    assert "not valid JSON" in problems[0]


def test_validate_subconfig_consal_test_fixture() -> None:
    """The real `.devcontainer/consal-test/` fixture used by
    tests/integration/test_container.py — checked for real, not just
    synthetic tmp_path fixtures, so a broken reference in it is caught
    here rather than only surfacing during a live `dco` run on the host.
    """
    repo_root = Path(__file__).resolve().parents[2]
    fixture_dir = repo_root / ".devcontainer" / "consal-test"
    assert validate_subconfig(fixture_dir) == []


def test_generate_subconfig_writes_valid_subconfig(tmp_path: Path) -> None:
    # devcontainer.json shares ../Dockerfile with the project's default
    # profile, which generate_subconfig doesn't itself create -- that's
    # dco's own self-heal job on first --sub-config use (or it's already
    # there in a real project). Simulate that state here.
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "Dockerfile").write_text("FROM scratch\n")

    subconfig_dir = generate_subconfig(tmp_path, "consal")

    assert subconfig_dir == tmp_path / ".devcontainer" / "consal"
    assert validate_subconfig(subconfig_dir) == []


def test_generate_subconfig_devcontainer_json_shares_dockerfile(tmp_path: Path) -> None:
    subconfig_dir = generate_subconfig(tmp_path, "consal")
    config = json.loads((subconfig_dir / "devcontainer.json").read_text())
    assert config["build"]["dockerfile"] == "../Dockerfile"


def test_generate_subconfig_guardrail_hook_is_executable(tmp_path: Path) -> None:
    subconfig_dir = generate_subconfig(tmp_path, "consal")
    hook = subconfig_dir / "guardrail-hook.sh"
    assert hook.stat().st_mode & 0o111


def test_generate_subconfig_writes_claude_settings_with_hook_registered(
    tmp_path: Path,
) -> None:
    generate_subconfig(tmp_path, "consal")
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    command = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    assert command == "bash /workspace/.devcontainer/consal/guardrail-hook.sh"


def test_generate_subconfig_copies_allowlist(tmp_path: Path) -> None:
    subconfig_dir = generate_subconfig(tmp_path, "consal")
    allowlist = (subconfig_dir / "allowlist.txt").read_text()
    assert "api.anthropic.com" in allowlist


def test_generate_subconfig_mounts_allowlist_with_real_subconfig_name(
    tmp_path: Path,
) -> None:
    """The template ships a __SUBCONFIG_NAME__ placeholder in the
    allowlist bind-mount source (the mount needs to know its own
    directory name, which varies per call) -- this must be substituted
    with the real name, never left in the generated file, and must match
    whatever subconfig_name was actually passed in (not hardcoded to
    "consal" specifically).
    """
    subconfig_dir = generate_subconfig(tmp_path, "custom-name")
    config = json.loads((subconfig_dir / "devcontainer.json").read_text())
    mounts = " ".join(config["mounts"])
    assert "__SUBCONFIG_NAME__" not in mounts
    assert ".devcontainer/custom-name/allowlist.txt" in mounts
    assert "target=/usr/local/etc/dco-allowlist.txt" in mounts


def test_generate_subconfig_references_pat_via_host_env_var(tmp_path: Path) -> None:
    """The PAT itself is never generated or written here — only a
    reference to a host env var Consal expects to already be set (see
    CONSAL_GOALS.md: injected via containerEnv, never committed).
    """
    subconfig_dir = generate_subconfig(tmp_path, "consal")
    config = json.loads((subconfig_dir / "devcontainer.json").read_text())
    assert config["containerEnv"]["GH_TOKEN"] == "${localEnv:CONSAL_GH_PAT}"
