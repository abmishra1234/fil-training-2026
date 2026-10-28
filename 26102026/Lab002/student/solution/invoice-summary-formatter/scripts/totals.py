"""
totals.py - deterministic invoice arithmetic for the invoice-summary-formatter skill.

Contract : scripts/totals_schema.json (JSON Schema 2020-12)
Input    : one JSON object on stdin
Output   : one JSON object on stdout
           success -> {"subtotal","gst","total","stated_total","difference","status"}   exit 0
           failure -> {"error","field","fix","retryable"}                               exit 2
Money is handled with Decimal (never float) and rounded half-up to 2 places.
Errors are written for the MODEL to read: what went wrong, how to fix it, whether to retry.

    echo '{"lines":[{"qty":2,"price":500}],"gst_rate":18}' | python scripts/totals.py
"""
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator # type: ignore

SCHEMA = json.loads((Path(__file__).parent / "totals_schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
RATES = ", ".join(str(r) for r in SCHEMA["properties"]["gst_rate"]["enum"])
TOLERANCE = Decimal("1.00")
CENT = Decimal("0.01")


def money(x) -> Decimal:
    # str() first: Decimal(0.1) would carry the float error, Decimal("0.1") does not
    return Decimal(str(x)).quantize(CENT, rounding=ROUND_HALF_UP)


def explain(err) -> dict:
    """Turn a jsonschema error into an actionable message for the agent."""
    field = err.json_path.replace("$.", "") if err.json_path != "$" else "(root)"
    v = err.validator
    if v == "required":
        missing = err.message.split("'")[1]
        fixes = {
            "gst_rate": f"Add gst_rate as a number, one of {RATES} (percent, e.g. 18).",
            "lines": "Add lines: a list of {description, qty, price} objects, one per invoice line.",
            "qty": "Add qty (a number greater than 0) to this line item.",
            "price": "Add price (the unit price in INR, 0 or more) to this line item.",
        }
        return {"error": f"'{missing}' is missing", "field": missing,
                "fix": fixes.get(missing, f"Add the field '{missing}'.")}
    if v == "enum":
        return {"error": f"{field} = {err.instance} is not an allowed GST rate", "field": field,
                "fix": f"Send gst_rate as one of {RATES}. If the invoice shows CGST + SGST, add the two rates."}
    if v == "minItems":
        return {"error": "lines is empty", "field": field,
                "fix": "Send at least one line item with qty and price."}
    if v == "additionalProperties":
        allowed = ", ".join(err.schema.get("properties", {}))
        return {"error": err.message, "field": field,
                "fix": f"Remove the unknown field(s). Allowed fields here: {allowed}."}
    if v in {"exclusiveMinimum", "minimum"}:
        rule = "greater than 0" if v == "exclusiveMinimum" else "0 or more"
        return {"error": f"{field} = {err.instance} is out of range", "field": field,
                "fix": f"{field} must be {rule}. Credit notes are handled by a different skill."}
    if v == "type":
        return {"error": f"{field} has the wrong type", "field": field,
                "fix": f"{field} must be of type {err.validator_value}, e.g. 18 not \"18%\"."}
    return {"error": err.message, "field": field, "fix": "Correct the input to match totals_schema.json."}


def fail(payload: dict):
    payload.setdefault("retryable", True)
    print(json.dumps(payload))
    sys.exit(2)


def validate(data):
    errs = sorted(VALIDATOR.iter_errors(data), key=lambda e: (len(e.path), e.json_path))
    return explain(errs[0]) if errs else None


def compute(data: dict) -> dict:
    subtotal = sum((money(Decimal(str(l["qty"])) * Decimal(str(l["price"]))) for l in data["lines"]),
                   Decimal("0"))
    gst = money(subtotal * Decimal(str(data["gst_rate"])) / Decimal(100))
    total = subtotal + gst
    out = {"subtotal": f"{subtotal:.2f}", "gst": f"{gst:.2f}", "total": f"{total:.2f}",
           "stated_total": None, "difference": None, "status": "OK"}
    if "stated_total" in data:
        stated = money(data["stated_total"])
        diff = stated - total
        out.update(stated_total=f"{stated:.2f}", difference=f"{diff:.2f}",
                   status="MISMATCH" if abs(diff) > TOLERANCE else "OK")
    return out

def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail({"error": f"input is not valid JSON ({e.msg} at char {e.pos})", "field": "(root)",
              "fix": "Send exactly one JSON object, for example "
                     "{\"lines\": [{\"qty\": 2, \"price\": 500}], \"gst_rate\": 18}."})
    problem = validate(data)
    if problem:
        fail(problem)
    print(json.dumps(compute(data)))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never leak a stack trace to the agent
        fail({"error": f"internal error: {type(e).__name__}", "field": "(none)",
              "fix": "Do not retry. Report this invoice to the AP team for manual processing.",
              "retryable": False})
