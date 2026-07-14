"""Self-consistency checks for Eigen-generated `dco` sub-config profiles.

Lesson carried forward (EIGEN_GOALS.md): a config's *result* must be
checked for self-consistency — every referenced path actually exists —
before it's ever handed to `dco`, without needing a real container build
to surface a gap.
"""

from __future__ import annotations

import json
from pathlib import Path


def validate_subconfig(subconfig_dir: Path) -> list[str]:
    """Return a list of problems with the sub-config, empty if none.

    Checks that devcontainer.json exists, parses, and that the paths it
    references (currently: build.dockerfile) resolve relative to
    ``subconfig_dir``.
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

    return problems


def generate_subconfig(target_dir: Path, project_id: str) -> Path:
    """Stamp out a `.devcontainer/eigen/` sub-config for a managed project.

    Not yet implemented — will copy the packaged template (devcontainer.json,
    allowlist, guardrail hook) into ``target_dir``, parameterized by
    ``project_id``.
    """
    raise NotImplementedError
