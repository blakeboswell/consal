"""Command-line entry point: `consal <subcommand>`."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="consal")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "doctor", help="run standing self-consistency/reachability checks"
    )
    subparsers.add_parser("run", help="run one autonomous scheduler tick")

    args = parser.parse_args(argv)

    if args.command == "doctor":
        print("consal doctor: not yet implemented")
        return 0
    if args.command == "run":
        print("consal run: not yet implemented")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
