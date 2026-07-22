"""Command-line entry point: `consal <subcommand>`.

CLI args are the canonical interface (see settings.py's docstring); a
project's `.consal/config.toml` just pre-fills the same values.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from consal import bootstrap, config, container, doctor as doctor_module
from consal.scheduler import dispatch_decomposition, run_loop_once
from consal.settings import (
    DEFAULT_SUB_CONFIG,
    Settings,
    SettingsError,
    load_config_file,
    resolve_settings,
    write_config_file,
)

PLAN_FILENAME = "PLAN.md"


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="project directory (default: current directory)",
    )
    parser.add_argument(
        "--project-id",
        default=None,
        help="runtime state namespace (default: from .consal/config.toml)",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="GitHub repo, owner/name (default: from .consal/config.toml)",
    )
    parser.add_argument(
        "--sub-config",
        default=None,
        help="dco sub-config name (default: from .consal/config.toml, or \"consal\")",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="consal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="generate a dco sub-config for this project"
    )
    _add_common_args(init_parser)
    init_parser.add_argument(
        "--create",
        action="store_true",
        help="create a brand-new GitHub repo (requires --repo); never forks",
    )

    attach_parser = subparsers.add_parser(
        "attach", help="attach an interactive session (planning, direct intervention)"
    )
    _add_common_args(attach_parser)

    doctor_parser = subparsers.add_parser(
        "doctor", help="run standing self-consistency/reachability checks"
    )
    _add_common_args(doctor_parser)

    run_parser = subparsers.add_parser("run", help="run one autonomous scheduler tick")
    _add_common_args(run_parser)

    plan_parser = subparsers.add_parser(
        "plan", help="decompose the project plan into GitHub issues"
    )
    _add_common_args(plan_parser)

    args = parser.parse_args(argv)

    if args.command == "init":
        return _cmd_init(args)

    if args.command == "attach":
        return _cmd_attach(args)

    try:
        settings = resolve_settings(
            workspace=args.workspace,
            project_id=args.project_id,
            repo=args.repo,
            sub_config=args.sub_config,
        )
    except SettingsError as exc:
        print(f"consal: error: {exc}", file=sys.stderr)
        return 1

    if args.command == "doctor":
        return doctor_module.run(settings)

    if args.command == "run":
        result = run_loop_once(
            settings.project_id, settings.workspace, settings.repo, settings.sub_config
        )
        if result.was_idle:
            print("consal run: idle, no open issues")
            return 0
        if result.turn.succeeded:
            print(f"consal run: issue #{result.issue_number}, turn succeeded")
            return 0
        print(
            f"consal run: issue #{result.issue_number}, turn failed "
            f"(exit {result.turn.exit_code})",
            file=sys.stderr,
        )
        return 1

    if args.command == "plan":
        return _cmd_plan(settings)

    return 1


def _cmd_init(args: argparse.Namespace) -> int:
    """`consal init`: generate the sub-config, and record whatever of
    project-id/repo/sub-config were given (or detected) in
    `.consal/config.toml` -- unlike `doctor`/`run`, nothing here is
    required. Generating the sub-config itself needs neither `project_id`
    nor `repo` (`config.generate_subconfig`'s own signature takes only a
    workspace and a sub-config name), so `init` doesn't force them up
    front; a project can fill them in later, by hand or via a later `init`
    call (which merges into the existing config file, never clobbers it).

    Two mutually exclusive paths, by construction:
    - `--create`: always requires an explicit `--repo`, always creates a
      brand-new GitHub repo from this workspace (`bootstrap.create_project`
      itself raises if an `origin` remote already exists -- "make
      something new" never means "adopt what's here").
    - Plain `init`: for an existing project. `--repo` is optional -- if
      the workspace already has an `origin` remote, it's detected and
      adopted automatically, so a directory that's already a real GitHub
      repo needs nothing but `consal init`.
    """
    workspace = (args.workspace or Path.cwd()).resolve()
    sub_config = args.sub_config or DEFAULT_SUB_CONFIG

    if args.create:
        if not args.repo:
            print(
                "consal: error: --create requires --repo owner/name",
                file=sys.stderr,
            )
            return 1
        try:
            bootstrap.create_project(workspace, sub_config, args.repo)
        except RuntimeError as exc:
            print(f"consal: error: {exc}", file=sys.stderr)
            return 1
        print(f"consal init: created {args.repo} and generated sub-config")
        repo = args.repo
    else:
        subconfig_dir = config.generate_subconfig(workspace, sub_config)
        print(f"consal init: generated sub-config at {subconfig_dir}")

        detected = bootstrap.detect_origin_repo(workspace)
        if detected and args.repo and detected != args.repo:
            print(
                f"consal: error: --repo {args.repo} doesn't match this "
                f"workspace's existing origin remote ({detected})",
                file=sys.stderr,
            )
            return 1
        repo = args.repo or detected
        if detected and not args.repo:
            print(f"consal init: detected existing remote, using {detected}")

    updates = {"sub_config": sub_config}
    if args.project_id:
        updates["project_id"] = args.project_id
    if repo:
        updates["repo"] = repo

    config_path = write_config_file(workspace, **updates)
    print(f"consal init: wrote {config_path}")
    return 0


def _cmd_attach(args: argparse.Namespace) -> int:
    """`consal attach`: interactive session (planning, direct
    intervention) -- the one place `dco` is invoked at all, and only
    internally; never needs `project_id`/`repo`, since interactive
    planning is often the first thing run right after `consal init`,
    before those are necessarily set.
    """
    workspace = (args.workspace or Path.cwd()).resolve()
    file_config = load_config_file(workspace)
    sub_config = args.sub_config or file_config.get("sub_config") or DEFAULT_SUB_CONFIG
    return container.attach_interactive(workspace, sub_config)


def _cmd_plan(settings: Settings) -> int:
    """`consal plan`: dispatch one plan-decomposition turn (see
    CONSAL_GOALS.md's "Plan decomposition" decision). Reads the plan from
    `PLAN.md` at the workspace root, the file step 2 of the workflow
    (interactive planning) produces.
    """
    plan_path = settings.workspace / PLAN_FILENAME
    if not plan_path.is_file():
        print(
            f"consal: error: no {PLAN_FILENAME} found in {settings.workspace}. "
            'Write the project plan there first (see CONSAL_GOALS.md\'s '
            '"The workflow", step 2).',
            file=sys.stderr,
        )
        return 1

    turn = dispatch_decomposition(
        settings.workspace, settings.sub_config, settings.repo, plan_path.read_text()
    )
    if turn.succeeded:
        print("consal plan: decomposition turn succeeded")
        return 0
    print(
        f"consal plan: decomposition turn failed (exit {turn.exit_code})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
