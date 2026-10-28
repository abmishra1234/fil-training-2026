"""
Tests for scripts/totals.py.   Run from the lab folder:   pytest -q

Each test sends JSON to the script exactly like an agent would, then checks
(1) the numbers, (2) that errors are actionable, (3) that no stack trace leaks out.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest # type: ignore

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "invoice-summary-formatter" / "scripts" / "totals.py"
if not SCRIPT.exists():  # trainer copy keeps the reference under solution/
    SCRIPT = ROOT / "solution" / "invoice-summary-formatter" / "scripts" / "totals.py"
INPUTS = ROOT / "inputs"
RATES = "0, 5, 12, 18, 28"


def run(payload):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    p = subprocess.run([sys.executable, str(SCRIPT)], input=raw, capture_output=True, text=True, timeout=20)
    assert "Traceback" not in p.stderr, "A stack trace reached the agent:\n" + p.stderr
    assert p.stdout.strip(), "The script printed nothing on stdout"
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        pytest.fail("stdout is not JSON: " + p.stdout[:200])
    return p.returncode, out


def from_file(name):
    return (INPUTS / name).read_text(encoding="utf-8")


# ---------- 1. correct numbers --------------------------------------------
def test_deck_example():
    code, out = run(from_file("valid_simple.json"))
    assert code == 0
    assert (out["subtotal"], out["gst"], out["total"]) == ("1000.00", "180.00", "1180.00")


def test_invoice_01_is_ok():
    code, out = run(from_file("inv01_clean.json"))
    assert code == 0
    assert out["total"] == "14750.00" and out["status"] == "OK"


def test_invoice_03_is_mismatch_by_1000():
    code, out = run(from_file("inv03_mismatch.json"))
    assert code == 0
    assert out["total"] == "40828.00"
    assert out["status"] == "MISMATCH" and out["difference"] == "1000.00"


def test_decimal_not_float():
    # with floats, 3 * 0.10 = 0.30000000000000004
    code, out = run({"lines": [{"qty": 3, "price": 0.10}], "gst_rate": 0})
    assert code == 0 and out["total"] == "0.30"


def test_round_half_up():
    # 30.30 * 18% = 5.454 -> 5.45 ;  12.50 * 5% = 0.625 -> 0.63 (half-up, not banker's)
    assert run({"lines": [{"qty": 3, "price": 10.10}], "gst_rate": 18})[1]["gst"] == "5.45"
    assert run({"lines": [{"qty": 1, "price": 12.50}], "gst_rate": 5})[1]["gst"] == "0.63"


def test_one_rupee_tolerance():
    _, out = run({"lines": [{"qty": 1, "price": 100}], "gst_rate": 18, "stated_total": 118.90})
    assert out["status"] == "OK"


# ---------- 2. actionable errors ------------------------------------------
def assert_actionable(code, out, must_mention):
    assert code == 2, "errors must exit with code 2"
    assert {"error", "fix", "retryable"} <= set(out), "error JSON needs error, fix and retryable"
    assert must_mention.lower() in out["fix"].lower(), f"the fix should mention: {must_mention}"


def test_missing_gst_rate_names_allowed_values():
    assert_actionable(*run(from_file("bad_missing_gst.json")), RATES)


def test_gst_18_5_rejected_by_contract():
    assert_actionable(*run(from_file("bad_gst_18_5.json")), RATES)


def test_empty_lines():
    assert_actionable(*run(from_file("bad_empty_lines.json")), "at least one")


def test_unknown_field_rejected():
    code, out = run({"lines": [{"qty": 1, "price": 5}], "gst_rate": 18, "discount": 10})
    assert_actionable(code, out, "remove")


def test_negative_quantity():
    code, out = run({"lines": [{"qty": -2, "price": 5}], "gst_rate": 18})
    assert_actionable(code, out, "greater than 0")


def test_gst_as_text():
    code, out = run({"lines": [{"qty": 1, "price": 5}], "gst_rate": "18%"})
    assert code == 2 and RATES in out["fix"]


def test_not_json_at_all():
    code, out = run("GST is 18 percent, two widgets at 500")
    assert_actionable(code, out, "json")
