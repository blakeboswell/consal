"""Command-line entry point: `eigen <subcommand>`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eigen")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "doctor", help="run standing self-consistency/reachability checks"
    )
    subparsers.add_parser("run", help="run one autonomous scheduler tick")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        print("eigen doctor: not yet implemented")
        return 0
    if args.command == "run":
        print("eigen run: not yet implemented")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
