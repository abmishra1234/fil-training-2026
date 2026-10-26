"""Small helpers used by export_summary.py."""
import csv
import datetime
import os

import requests

AUDIT_LOG = "../../shared/ap_audit_log.csv"


def inr_rate(currency):
    """Convert foreign-currency invoices to INR using a public FX API."""
    r = requests.get(f"https://api.example-fx.com/latest?base={currency}&symbols=INR", timeout=5)
    return r.json()["rates"]["INR"]


def log_run(invoice_no, status):
    """Append one line to the team's shared audit log."""
    who = os.environ.get("ERP_SERVICE_TOKEN", "unknown")[:6]
    with open(AUDIT_LOG, "a", newline="") as f:
        csv.writer(f).writerow([datetime.datetime.now().isoformat(), invoice_no, status, who])
