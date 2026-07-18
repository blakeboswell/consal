"""Resolve Consal's per-project settings from CLI args, a checked-in
project config file, and built-in defaults, in that precedence order.

CLI args are the canonical interface — the config file exists purely to
pre-fill the same values, not as a parallel code path. `project_id`/`repo`
get no built-in default: guessing wrong here could point the scheduler at
the wrong GitHub repo or collide two projects' runtime state directories,
so both must come from an explicit `--flag` or the config file, or this
raises rather than silently picking something.

The config file (`.consal/config.toml`) is static, project-level config —
like the sub-config profile itself, it belongs checked into the project's
own repo, not in the churny, host-side `~/.consal/<project_id>/` runtime
state directory (see CONSAL_GOALS.md's profile-vs-runtime-state split).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_RELATIVE_PATH = Path(".consal") / "config.toml"
DEFAULT_SUB_CONFIG = "consal"


class SettingsError(Exception):
    """Raised when a required setting is missing from both CLI args and
    the project config file."""


@dataclass(frozen=True)
class Settings:
    workspace: Path
    project_id: str
    repo: str
    sub_config: str


def load_config_file(workspace: Path) -> dict:
    """Return the parsed contents of `<workspace>/.consal/config.toml`,
    or an empty dict if it doesn't exist."""
    path = workspace / CONFIG_RELATIVE_PATH
    if not path.is_file():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def resolve_settings(
    workspace: Path | None = None,
    project_id: str | None = None,
    repo: str | None = None,
    sub_config: str | None = None,
) -> Settings:
    """Resolve final settings: explicit arg > config file value > default.

    `workspace` defaults to cwd (matching `dco`'s own convention for its
    positional `[path]`). `sub_config` defaults to `"consal"`.
    `project_id`/`repo` have no default — raises `SettingsError` if
    neither an arg nor the config file supplies them.
    """
    resolved_workspace = (workspace or Path.cwd()).resolve()
    config = load_config_file(resolved_workspace)

    resolved_project_id = project_id or config.get("project_id")
    resolved_repo = repo or config.get("repo")
    resolved_sub_config = sub_config or config.get("sub_config") or DEFAULT_SUB_CONFIG

    missing = [
        name
        for name, value in (
            ("project-id", resolved_project_id),
            ("repo", resolved_repo),
        )
        if not value
    ]
    if missing:
        config_path = resolved_workspace / CONFIG_RELATIVE_PATH
        raise SettingsError(
            f"missing required setting(s): {', '.join(missing)} -- pass via "
            f"--{' / --'.join(missing)}, or set in {config_path}"
        )

    return Settings(
        workspace=resolved_workspace,
        project_id=resolved_project_id,
        repo=resolved_repo,
        sub_config=resolved_sub_config,
    )
