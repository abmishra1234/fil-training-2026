"""
Group E - Design and contract: new secret types without touching the core, a clean
GatewayResult contract, robustness on unusual input.                                JT23 - JT25
"""
from __future__ import annotations

import copy
import re

import adapter
from samples import CLEAN_TEXT, SK_KEY, VISA_SPACES, handbook_like

P = adapter.make_passage
V = adapter.result_view
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")


def test_JT23_new_secret_type_plugs_in_without_core_changes():
    """Add an EMAIL type from the outside: detected in passages and query, old types still work."""
    det = adapter.make_custom_detector("EMAIL", lambda t: len(EMAIL.findall(t)))
    gw = adapter.make_gateway(extra_detectors=[det])
    ps = [P("a#0", "Contact ravi.k@example.com for access."), P("a#1", CLEAN_TEXT), P("a#2", f"card {VISA_SPACES}")]
    r = V(gw.check("who approves access?", ps))
    assert r["safe_ids"] == ["a#1"]
    assert r["dropped"] == ["a#0", "a#2"]
    f = {k: v for k, v in r["findings"].items() if v}
    assert f == {"EMAIL": 1, adapter.TYPE_CARD: 1}
    q = V(gw.check("mail me at x.y@example.org", [P("b#0", CLEAN_TEXT)]))
    assert q["decision"] == "BLOCK_QUERY" and q["findings"].get("EMAIL", 0) == 1

    # two extra types at once, order independent
    det2 = adapter.make_custom_detector("EMPLOYEE_ID", lambda t: len(re.findall(r"\bEMP-\d{6}\b", t)))
    gw2 = adapter.make_gateway(extra_detectors=[det2, det])
    r2 = V(gw2.check("q", [P("c#0", "EMP-123456 and EMP-654321"), P("c#1", CLEAN_TEXT)]))
    assert r2["dropped"] == ["c#0"] and r2["findings"].get("EMPLOYEE_ID") == 2


def test_JT24_result_contract_identity_order_purity():
    """Same passage OBJECTS returned in order; ids are strings; input never mutated; no state between calls."""
    ps = [P("r#0", CLEAN_TEXT), P("r#1", f"key {SK_KEY}"), P("r#2", "Anchor days Tue/Thu"), P("r#3", "Project Falcon")]
    before = copy.deepcopy(ps)
    ids_before = [id(p) for p in ps]
    r1 = V(adapter.check("anchor days?", ps))
    assert [id(p) for p in ps] == ids_before and ps == before, "the input list / passages were modified"
    assert r1["decision"] in {"ALLOW", "BLOCK_QUERY", "BLOCK_CONTEXT", "BLOCK_ERROR"}
    assert r1["safe"][0] is ps[0] and r1["safe"][1] is ps[2], "return the caller's passage objects, in order"
    assert r1["dropped"] == ["r#1", "r#3"] and all(isinstance(x, str) for x in r1["dropped"])
    assert all(isinstance(k, str) and isinstance(v, int) and v >= 0 for k, v in r1["findings"].items())
    # deterministic and stateless: same input, same output; a blocked call does not poison the next one
    adapter.check(f"leak {SK_KEY}", ps)
    r2 = V(adapter.check("anchor days?", ps))
    assert (r2["decision"], r2["safe_ids"], r2["dropped"], r2["findings"]) == \
           (r1["decision"], r1["safe_ids"], r1["dropped"], r1["findings"])


def test_JT25_robust_on_empty_unicode_and_large_input():
    """Empty lists, empty query, Unicode and very large clean input are handled without errors."""
    r = V(adapter.check("anchor days?", []))
    assert r["decision"] not in ("BLOCK_QUERY", "BLOCK_ERROR") and r["safe"] == [] and r["dropped"] == []
    r = V(adapter.check("", [P("u#0", CLEAN_TEXT)]))
    assert r["decision"] == "ALLOW" and r["safe_ids"] == ["u#0"]
    uni = "छुट्टी नीति: अर्जित अवकाश 1.5 दिन प्रति माह 🌴 — café naïve résumé 日本語"
    r = V(adapter.check("अवकाश?", [P("u#1", uni)]))
    assert r["decision"] == "ALLOW" and r["safe_ids"] == ["u#1"]
    r = V(adapter.check("q", [P("u#2", f"मेरा कार्ड {VISA_SPACES} है")]))
    assert r["dropped"] == ["u#2"], "a card inside non-English text is still a card"
    many = [P(f"m#{i}", handbook_like(300, str(i))) for i in range(100)]
    big = P("big#0", handbook_like(200_000))
    r = V(adapter.check("q", many + [big]))
    assert r["decision"] == "ALLOW" and len(r["safe"]) == 101
