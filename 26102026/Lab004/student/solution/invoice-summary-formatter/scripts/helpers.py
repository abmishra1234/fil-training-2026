"""Small helpers used by export_summary.py.

Gate fixes (Lab 4):
  * removed inr_rate(): network egress for a feature the skill does not need
    (FIL AP invoices are in INR; foreign-currency invoices go to a different skill)
  * removed the ERP_SERVICE_TOKEN read: a credential the skill has no reason to touch
  * audit log moved from ../../shared/ (outside the skill's sandbox) to ./output/
"""
import csv
import datetime

AUDIT_LOG = "output/audit_log.csv"


def log_run(invoice_no, status):
    """Append one line to this skill's own audit log."""
    with open(AUDIT_LOG, "a", newline="") as f:
        csv.writer(f).writerow([datetime.datetime.now().isoformat(), invoice_no, status])
