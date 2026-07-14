"""Generate and self-consistency-check Eigen's `dco` sub-config profiles.

Lesson carried forward (EIGEN_GOALS.md): a config's *result* must be
checked for self-consistency — every referenced path actually exists —
before it's ever handed to `dco`, without needing a real container build
to surface a gap.

The guardrail hook shipped here (`templates/guardrail-hook.sh`) is
autonomy-specific policy, so it's authored and owned in Eigen, not `dco` —
see EIGEN_GOALS.md's architecture rationale and the correction under
"Eigen/`dco` interface" (there's no Python-side reimplementation of this
policy: a Claude Code `PreToolUse` hook has to be a shell command, so a
parallel Python checker would never run in the real enforcement path).
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

    return problems


def generate_subconfig(project_root: Path, subconfig_name: str) -> Path:
    """Stamp out a `.devcontainer/<subconfig_name>/` sub-config for a
    project Eigen manages, plus a `.claude/settings.json` at the project
    root registering the guardrail hook as a `PreToolUse` hook.

    Copies the packaged templates as-is (devcontainer.json shares
    `../Dockerfile` with the project's default profile — see
    EIGEN_GOALS.md's "Eigen/`dco` interface" decision; the PAT itself is
    never written here, only referenced via `containerEnv`'s
    `${localEnv:EIGEN_GH_PAT}`, so it's the caller's job to set that env
    var on the host, never to commit it). Returns the sub-config directory.
    """
    subconfig_dir = project_root / ".devcontainer" / subconfig_name
    subconfig_dir.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(
        TEMPLATES_DIR / "devcontainer.json", subconfig_dir / "devcontainer.json"
    )

    hook_dest = subconfig_dir / "guardrail-hook.sh"
    shutil.copyfile(TEMPLATES_DIR / "guardrail-hook.sh", hook_dest)
    hook_dest.chmod(0o755)

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
