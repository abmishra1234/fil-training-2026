"""Entry point required by the contract:

    python -m counterstrike run --data data --out out

Replace the body of `run` with your fleet. Keep the arguments.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="counterstrike")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--data", default="data")
    r.add_argument("--out", default="out")
    args = p.parse_args(argv)
    if args.cmd == "run":
        print("TODO: implement the agent fleet", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
