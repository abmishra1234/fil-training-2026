"""Unit tests for the Action (quality evals for the deterministic part).

    cd expense-claim-checker && pytest -q evals/
"""
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
HR = "../mock_connectors/hr_employees.json"
INPUTS = SKILL / "evals" / "inputs"


def run(payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, "scripts/policy_check.py", "--hr-data", HR], cwd=SKILL,
                       input=raw, capture_output=True, text=True, timeout=20)
    assert "Traceback" not in p.stderr
    return p.returncode, json.loads(p.stdout)


def claim(**kw):
    base = {"employee_id": "FIL1023", "city": "Pune", "submitted_on": "2026-10-22",
            "items": [{"date": "2026-10-20", "category": "meals", "amount": 400, "receipt": True}]}
    base.update(kw)
    return base


def test_sample_1_approve():
    _, out = run((INPUTS / "claim_01_neha.json").read_text())
    assert out["status"] == "APPROVE" and out["approvable"] == "8270.00"


def test_sample_2_partial():
    _, out = run((INPUTS / "claim_02_aarav.json").read_text())
    assert (out["status"], out["approvable"], out["excess"]) == ("PARTIAL", "4600.00", "2950.00")
    assert {f["verdict"] for f in out["findings"]} == {"OVER_LIMIT", "NO_RECEIPT", "NOT_ALLOWED"}


def test_sample_3_unknown_employee():
    _, out = run((INPUTS / "claim_03_unknown.json").read_text())
    assert out["status"] == "NEEDS_INFO"


def test_meals_are_added_per_day():
    items = [{"date": "2026-10-20", "category": "meals", "amount": 400, "receipt": True},
             {"date": "2026-10-20", "category": "meals", "amount": 300, "receipt": True}]
    _, out = run(claim(items=items))  # L1 limit 600/day
    assert out["approvable"] == "600.00" and out["status"] == "PARTIAL"


def test_tier2_hotel_limit():
    items = [{"date": "2026-10-20", "category": "hotel", "amount": 3500, "receipt": True}]
    _, out = run(claim(city="Jaipur", items=items))  # L1 tier-2 = 3000
    assert out["city_tier"] == 2 and out["approvable"] == "3000.00"


def test_late_item():
    items = [{"date": "2026-09-01", "category": "meals", "amount": 300, "receipt": True}]
    _, out = run(claim(items=items))
    assert out["status"] == "REJECT" and out["findings"][0]["verdict"] == "LATE"


def test_small_item_without_receipt_is_fine():
    items = [{"date": "2026-10-20", "category": "meals", "amount": 500, "receipt": False}]
    assert run(claim(items=items))[1]["status"] == "APPROVE"


def test_bad_category_is_actionable():
    items = [{"date": "2026-10-20", "category": "laptop", "amount": 50000, "receipt": True}]
    code, out = run(claim(items=items))
    assert code == 2 and "other" in out["fix"]


def test_bad_date_format_is_actionable():
    code, out = run(claim(submitted_on="22/10/2026"))
    assert code == 2 and "YYYY-MM-DD" in out["fix"]


def test_connector_down_is_not_retryable():
    p = subprocess.run([sys.executable, "scripts/policy_check.py", "--hr-data", "missing.json"], cwd=SKILL,
                       input=json.dumps(claim()), capture_output=True, text=True)
    out = json.loads(p.stdout)
    assert p.returncode == 2 and out["retryable"] is False
