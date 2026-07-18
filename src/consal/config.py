"""Generate and self-consistency-check Consal's `dco` sub-config profiles.

Lesson carried forward (CONSAL_GOALS.md): a config's *result* must be
checked for self-consistency — every referenced path actually exists —
before it's ever handed to `dco`, without needing a real container build
to surface a gap.

The guardrail hook shipped here (`templates/guardrail-hook.sh`) is
autonomy-specific policy, so it's authored and owned in Consal, not `dco`
— see CONSAL_GOALS.md's architecture rationale and the correction under
"Consal/`dco` interface" (there's no Python-side reimplementation of this
policy: a Claude Code `PreToolUse` hook has to be a shell command, so a
parallel Python checker would never run in the real enforcement path).

`templates/allowlist.txt` is bind-mounted over the shared, empty
top-level `.devcontainer/allowlist.txt` at container-start (see
`devcontainer.json`'s `mounts` entry) — see CONSAL_GOALS.md's "Isolation &
safety goals" correction: this locks down egress specifically for
containers carrying `CLAUDE_CODE_OAUTH_TOKEN`, without touching the
default profile's own (currently open) firewall posture.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def validate_subconfig(subconfig_dir: Path) -> list[str]:
    """Return a list of problems with the sub-config, empty if none.

    Checks that devcontainer.json exists, parses, and that the paths it
    references (currently: build.dockerfile) resolve relative to
    ``subconfig_dir``, and that the guardrail hook script is present.
    """
    devcontainer_json = subconfig_dir / "devcontainer.json"
    if not devcontainer_json.is_file():
        return [f"missing devcontainer.json in {subconfig_dir}"]

    try:
        config = json.loads(devcontainer_json.read_text())
    except json.JSONDecodeError as exc:
        return [f"devcontainer.json is not valid JSON: {exc}"]

    problems: list[str] = []

    dockerfile = config.get("build", {}).get("dockerfile")
    if dockerfile:
        dockerfile_path = (subconfig_dir / dockerfile).resolve()
        if not dockerfile_path.is_file():
            problems.append(f"referenced dockerfile not found: {dockerfile_path}")

    if not (subconfig_dir / "guardrail-hook.sh").is_file():
        problems.append(f"missing guardrail-hook.sh in {subconfig_dir}")

    if not (subconfig_dir / "allowlist.txt").is_file():
        problems.append(f"missing allowlist.txt in {subconfig_dir}")

    return problems


def generate_subconfig(project_root: Path, subconfig_name: str) -> Path:
    """Stamp out a `.devcontainer/<subconfig_name>/` sub-config for a
    project Consal manages, plus a `.claude/settings.json` at the project
    root registering the guardrail hook as a `PreToolUse` hook.

    Copies the packaged templates (devcontainer.json shares `../Dockerfile`
    with the project's default profile — see CONSAL_GOALS.md's "Consal/`dco`
    interface" decision; the PAT itself is never written here, only
    referenced via `containerEnv`'s `${localEnv:CONSAL_GH_PAT}`, so it's the
    caller's job to set that env var on the host, never to commit it).
    devcontainer.json isn't copied verbatim: it carries a
    `__SUBCONFIG_NAME__` placeholder in its allowlist bind-mount source
    (the mount needs its own sub-config's directory name, which varies per
    call), substituted here with the real ``subconfig_name``. Returns the
    sub-config directory.
    """
    subconfig_dir = project_root / ".devcontainer" / subconfig_name
    subconfig_dir.mkdir(parents=True, exist_ok=True)

    devcontainer_json = (TEMPLATES_DIR / "devcontainer.json").read_text()
    devcontainer_json = devcontainer_json.replace("__SUBCONFIG_NAME__", subconfig_name)
    (subconfig_dir / "devcontainer.json").write_text(devcontainer_json)

    hook_dest = subconfig_dir / "guardrail-hook.sh"
    shutil.copyfile(TEMPLATES_DIR / "guardrail-hook.sh", hook_dest)
    hook_dest.chmod(0o755)

    shutil.copyfile(
        TEMPLATES_DIR / "allowlist.txt", subconfig_dir / "allowlist.txt"
    )

    claude_dir = project_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                f"bash /workspace/.devcontainer/"
                                f"{subconfig_name}/guardrail-hook.sh"
                            ),
                        }
                    ],
                }
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")

    return subconfig_dir
