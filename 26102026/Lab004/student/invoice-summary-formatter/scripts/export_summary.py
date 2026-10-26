"""
export_summary.py - save the final invoice summary for the reviewer.

    python scripts/export_summary.py <invoice_no> <status> < summary.md
"""
import re
import sys
from os import environ as env
from pathlib import Path

from helpers import log_run


def main(invoice_no, status, summary_text):
    reviewer = env.get("AP_REVIEWER_EMAIL", "ap-review@fil.example")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", invoice_no)
    out = Path("output")
    out.mkdir(exist_ok=True)
    (out / f"{safe}.md").write_text(f"Reviewer: {reviewer}\n\n{summary_text}", encoding="utf-8")
    log_run(invoice_no, status)
    print(f"saved output/{safe}.md")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.stdin.read())
