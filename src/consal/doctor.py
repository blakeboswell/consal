"""`consal doctor`: standing self-consistency/reachability checks against
the real environment — distinct from the test suite, which checks the
code's logic against mocks and fixtures, never the actual machine it runs
on. This is what CONSAL_GOALS.md's lessons #1 (config self-consistency)
and #2 (standing reachability, not a one-time assertion) become as a real,
repeatable product feature, per the testing-strategy decision: "the live
check itself ships as a product feature... not a CI assertion — network
state isn't CI's job to assert."
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess

from consal import config
from consal.settings import Settings


def _report(label: str, ok: bool, detail: str = "") -> bool:
    status = "OK" if ok else "FAIL"
    suffix = f" -- {detail}" if detail and not ok else ""
    print(f"[{status}] {label}{suffix}")
    return ok


def check_environment() -> bool:
    """Prerequisite binaries/credentials on this host -- the same category
    of thing tests/integration/test_environment.py checks, but as a real
    command a human runs against their own machine, with readable output,
    not pytest assertions only exercised on the host running the suite.
    """
    checks = [
        _report("dco on PATH", shutil.which("dco") is not None),
        _report("devcontainer CLI on PATH", shutil.which("devcontainer") is not None),
    ]

    gh_auth = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    checks.append(_report("gh authenticated", gh_auth.returncode == 0, gh_auth.stderr.strip()))

    checks.append(
        _report(
            "CONSAL_GH_PAT set",
            bool(os.environ.get("CONSAL_GH_PAT")),
            "not set -- containerEnv's ${localEnv:CONSAL_GH_PAT} will resolve empty",
        )
    )
    checks.append(
        _report(
            "CLAUDE_CODE_OAUTH_TOKEN set",
            bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")),
            "not set -- claude -p will fail with 'Not logged in' inside the container",
        )
    )
    return all(checks)


def check_subconfig(settings: Settings) -> bool:
    """Lesson #1: a config's *result* checked for self-consistency, not
    taken on faith -- every referenced path actually exists.
    """
    subconfig_dir = settings.workspace / ".devcontainer" / settings.sub_config
    problems = config.validate_subconfig(subconfig_dir)
    ok = _report(f"sub-config self-consistent ({subconfig_dir})", not problems)
    for problem in problems:
        print(f"       - {problem}")
    return ok


def check_allowlist_reachability(settings: Settings) -> bool:
    """Lesson #2: an actual standing check that each allowlist entry
    resolves, not a one-time assertion taken on faith that the list is
    correct because it's written down.
    """
    allowlist_path = settings.workspace / ".devcontainer" / settings.sub_config / "allowlist.txt"
    if not allowlist_path.is_file():
        return _report("allowlist domains resolve", False, f"{allowlist_path} not found")

    domains = [
        line.strip()
        for line in allowlist_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not domains:
        return _report("allowlist domains resolve", True, "allowlist is empty")

    checks = []
    for domain in domains:
        try:
            socket.getaddrinfo(domain, None)
            resolved = True
        except socket.gaierror:
            resolved = False
        checks.append(_report(f"  {domain} resolves", resolved))
    return all(checks)


def run(settings: Settings) -> int:
    """Run every check, print a report, return 0 only if all passed."""
    results = [
        check_environment(),
        check_subconfig(settings),
        check_allowlist_reachability(settings),
    ]
    return 0 if all(results) else 1
