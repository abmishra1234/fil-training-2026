"""
export_summary.py - save the final invoice summary for the reviewer.

    python scripts/export_summary.py <invoice_no> <status> [reviewer] < summary.md

Gate fix (Lab 4, found in neighbour review): the reviewer used to come from an
environment variable via `from os import environ as env`. The gate did NOT catch
that alias. The reviewer is now an explicit argument, so nothing is read from env.
"""
import re
import sys
from pathlib import Path

from helpers import log_run


def main(invoice_no, status, summary_text, reviewer="ap-review@fil.example"):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", invoice_no)
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / f"{safe}.md").write_text(f"Reviewer: {reviewer}\n\n{summary_text}", encoding="utf-8")
    log_run(invoice_no, status)
    print(f"saved output/{safe}.md")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], args[1], sys.stdin.read(), *args[2:3])
