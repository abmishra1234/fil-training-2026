"""
policy_check.py - deterministic FIL travel-expense policy check (the skill's Action).

    python scripts/policy_check.py --hr-data ../mock_connectors/hr_employees.json < claim.json

Contract : scripts/claim_schema.json (JSON Schema 2020-12)
Connector: --hr-data is the MOCK of the HR system of record. In production this lookup is
           the HR MCP server's get_employee tool, called on behalf of the user.
Output   : {"employee", "city_tier", "claimed", "approvable", "excess", "status", "findings"}
           status: APPROVE | PARTIAL | REJECT | NEEDS_INFO
Errors   : {"error", "field", "fix", "retryable"}, exit code 2
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator # type: ignore

HERE = Path(__file__).parent
SCHEMA = json.loads((HERE / "claim_schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)

# Policy numbers mirror references/expense_policy.md (knowledge owner: Finance Policy team).
LIMITS = {  # grade: (meals per day, hotel tier-1, hotel tier-2, local travel per day)
    "L1": (600, 4000, 3000, 1500),
    "L2": (900, 6000, 4500, 1500),
    "L3": (1200, 8000, 6000, 2500),
}
TIER1 = {"mumbai", "delhi", "new delhi", "gurgaon", "gurugram", "noida", "bengaluru",
         "bangalore", "chennai", "hyderabad", "kolkata", "pune"}
NOT_ALLOWED = {"alcohol", "beer", "wine", "liquor", "bar", "fine", "penalty", "challan", "movie"}
RECEIPT_ABOVE = Decimal("500")
MAX_AGE_DAYS = 30
CENT = Decimal("0.01")


def money(x):
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(x):
    return f"{x:.2f}"


def fail(payload):
    payload.setdefault("retryable", True)
    print(json.dumps(payload))
    sys.exit(2)


def explain(err):
    field = err.json_path.replace("$.", "") if err.json_path != "$" else "(root)"
    v = err.validator
    if v == "required":
        missing = err.message.split("'")[1]
        return {"error": f"'{missing}' is missing", "field": missing,
                "fix": f"Add '{missing}'. Required: employee_id (e.g. FIL1023), city, submitted_on "
                       f"(YYYY-MM-DD) and items; each item needs date, category, amount, receipt."}
    if v == "enum":
        return {"error": f"{field} = {err.instance!r} is not allowed", "field": field,
                "fix": f"Use one of {', '.join(err.validator_value)}. Anything else goes in 'other' with a description."}
    if v == "pattern":
        return {"error": f"{field} = {err.instance!r} has the wrong format", "field": field,
                "fix": "employee_id looks like FIL1023; dates look like 2026-10-14 (YYYY-MM-DD)."}
    if v == "minItems":
        return {"error": "items is empty", "field": field, "fix": "Send at least one expense item."}
    if v == "exclusiveMinimum":
        return {"error": f"{field} must be more than 0", "field": field,
                "fix": "Send the amount in INR as a positive number. Refunds are not handled here."}
    if v == "additionalProperties":
        return {"error": err.message, "field": field,
                "fix": f"Remove unknown fields. Allowed: {', '.join(err.schema.get('properties', {}))}."}
    if v == "type":
        return {"error": f"{field} has the wrong type", "field": field,
                "fix": f"{field} must be {err.validator_value} (e.g. amount 850, receipt true)."}
    return {"error": err.message, "field": field, "fix": "Match scripts/claim_schema.json."}


def check(claim, hr):
    emp = next((e for e in hr["employees"] if e["emp_id"] == claim["employee_id"]), None)
    claimed = sum((money(i["amount"]) for i in claim["items"]), Decimal("0"))
    if emp is None:
        return {"employee": {"id": claim["employee_id"], "name": None, "grade": None},
                "city_tier": None, "claimed": fmt(claimed), "approvable": "0.00", "excess": "0.00",
                "status": "NEEDS_INFO",
                "findings": [{"verdict": "UNKNOWN_EMPLOYEE",
                              "reason": f"{claim['employee_id']} not found in HR records; confirm the employee ID."}]}

    meals, hotel1, hotel2, local = LIMITS[emp["grade"]]
    tier = 1 if claim["city"].strip().lower() in TIER1 else 2
    limit = {"meals": meals, "hotel": hotel1 if tier == 1 else hotel2, "local_travel": local}
    submitted = date.fromisoformat(claim["submitted_on"])

    findings, groups = [], defaultdict(lambda: Decimal("0"))
    approvable = Decimal("0")
    for it in claim["items"]:
        amt, d = money(it["amount"]), date.fromisoformat(it["date"])
        desc = it.get("description", "").lower()
        base = {"date": it["date"], "category": it["category"], "claimed": fmt(amt), "approvable": "0.00"}
        if (submitted - d).days > MAX_AGE_DAYS:
            findings.append({**base, "verdict": "LATE", "reason": f"submitted more than {MAX_AGE_DAYS} days after the expense"})
        elif it["category"] == "other" and any(w in desc.replace(",", " ").split() for w in NOT_ALLOWED):
            findings.append({**base, "verdict": "NOT_ALLOWED", "reason": "not reimbursable under policy section 4"})
        elif amt > RECEIPT_ABOVE and not it["receipt"]:
            findings.append({**base, "verdict": "NO_RECEIPT", "reason": "receipt required above INR 500"})
        elif it["category"] == "other":
            approvable += amt
        else:
            groups[(it["date"], it["category"])] += amt

    for (d, cat), amt in sorted(groups.items()):
        cap = Decimal(limit[cat])
        ok = min(amt, cap)
        approvable += ok
        if amt > cap:
            findings.append({"date": d, "category": cat, "claimed": fmt(amt), "approvable": fmt(ok),
                             "verdict": "OVER_LIMIT",
                             "reason": f"{emp['grade']} limit is INR {cap:,} per {'night' if cat == 'hotel' else 'day'}"
                                       + (f" in tier-{tier} cities" if cat == "hotel" else "")})

    status = "APPROVE" if approvable == claimed else ("REJECT" if approvable == 0 else "PARTIAL")
    return {"employee": {"id": emp["emp_id"], "name": emp["name"], "grade": emp["grade"]},
            "city_tier": tier, "claimed": fmt(claimed), "approvable": fmt(approvable),
            "excess": fmt(claimed - approvable), "status": status, "findings": findings}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hr-data", required=True, help="mock HR connector JSON")
    a = ap.parse_args()
    try:
        claim = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        fail({"error": f"input is not valid JSON ({e.msg})", "field": "(root)",
              "fix": "Send one JSON object with employee_id, city, submitted_on and items."})
    errs = sorted(VALIDATOR.iter_errors(claim), key=lambda e: (len(e.path), e.json_path))
    if errs:
        fail(explain(errs[0]))
    try:
        hr = json.loads(Path(a.hr_data).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail({"error": "HR connector unavailable", "field": "(connector)",
              "fix": "Do not retry now. Tell the user the HR system is unreachable and set Status to NEEDS_INFO.",
              "retryable": False})
    print(json.dumps(check(claim, hr), indent=1))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never leak a stack trace to the agent
        fail({"error": f"internal error: {type(e).__name__}", "field": "(none)",
              "fix": "Do not retry. Send this claim to the Finance team for manual review.", "retryable": False})
