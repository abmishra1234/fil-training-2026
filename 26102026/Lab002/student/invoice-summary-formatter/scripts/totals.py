"""
totals.py - deterministic invoice arithmetic (STARTER - complete the TODOs).

Contract : scripts/totals_schema.json (JSON Schema 2020-12)
Input    : one JSON object on stdin
Output   : success -> {"subtotal","gst","total","stated_total","difference","status"}  exit 0
           failure -> {"error","fix","retryable"}                                       exit 2

    echo '{"lines":[{"qty":2,"price":500}],"gst_rate":18}' | python scripts/totals.py
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = json.loads((Path(__file__).parent / "totals_schema.json").read_text(encoding="utf-8"))
V = Draft202012Validator(SCHEMA)


def fail(msg, fix):
    print(json.dumps({"error": msg, "fix": fix, "retryable": True}))
    sys.exit(2)


data = json.load(sys.stdin)          # TODO 4: invalid JSON must also return an actionable error
errs = sorted(V.iter_errors(data), key=str)
if errs:
    e = errs[0]
    fail(e.message, "Check field: " + e.json_path)   # TODO 3: make the fix specific per error type

# TODO 2: compute with Decimal (never float), rounded half-up to 2 places:
#   line amount = qty * price;  subtotal = sum of line amounts
#   gst = subtotal * gst_rate / 100;  total = subtotal + gst
#   if "stated_total" is given: difference = stated_total - total,
#       status = "MISMATCH" if abs(difference) > 1.00 else "OK"
# TODO 2b: print the result JSON, money as strings like "1180.00"
