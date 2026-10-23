"""
Group F - Constraints: never log secret text (types and counts only), < 20 ms for one
query plus 5 passages of about 2,000 characters.                                    JT26 - JT28
"""
from __future__ import annotations

import adapter
import pytest
from conftest import capture_everything, log_text, median_ms
from samples import AKIA_KEY, ALL_SECRET_STRINGS, AMEX, CLEAN_TEXT, CLIENT_SECRET, SK_KEY, VISA_SPACES, handbook_like

P = adapter.make_passage
V = adapter.result_view
LIMIT_MS = 20.0


def test_JT26_logs_and_console_never_contain_secret_text():
    """Run every decision type; no secret appears in any log record or on stdout/stderr, and blocks are audited by TYPE."""
    with capture_everything() as (handler, out, err):
        adapter.check(f"why is {AKIA_KEY} failing?", [P("l#0", CLEAN_TEXT)])                       # BLOCK_QUERY
        adapter.check("finance?", [P("l#1", f"card {VISA_SPACES} / {AMEX}"), P("l#2", CLEAN_TEXT)])  # partial drop
        adapter.check("all?", [P("l#3", f"key {SK_KEY}"), P("l#4", CLIENT_SECRET),
                               P("l#5", "PROJECT FALCON and Project Monsoon")])                      # BLOCK_CONTEXT
        adapter.check("clean?", [P("l#6", CLEAN_TEXT)])                                             # ALLOW
    text = log_text(handler) + out.getvalue() + err.getvalue()
    leaked = [s for s in ALL_SECRET_STRINGS if s in text]
    assert not leaked, f"secret text written to logs/console: {leaked}"
    assert any(t in text for t in (adapter.TYPE_CREDENTIAL, adapter.TYPE_CARD, adapter.TYPE_CODENAME)), \
        "blocked requests must be logged with the secret TYPE and count (audit trail), not silently"


def test_JT27_latency_one_query_five_2000_char_passages():
    """Realistic load: median of 40 runs must be under 20 ms (one passage holds a secret)."""
    query = "What is the per diem for Pune and how fast must a Sev-2 be acknowledged? " * 2
    ps = [P(f"t#{i}", handbook_like(2000, f"section {i}")) for i in range(5)]
    ps[3] = P("t#3", handbook_like(1950, f"ops note password=Winter2026! {CLEAN_TEXT}"))
    assert all(1900 <= len(p.text) <= 2000 for p in ps)
    result = V(adapter.check(query, ps))
    assert result["dropped"] == ["t#3"]
    ms = median_ms(lambda: adapter.check(query, ps))
    assert ms < LIMIT_MS, f"median {ms:.2f} ms >= {LIMIT_MS} ms"


@pytest.mark.parametrize("name, text", [
    ("digit-run", "1 " * 1000),
    ("dash-digits", "4111-" * 400),
    ("long-number", "7" * 2000),
    ("keyword-flood", "password secret api_key " * 84),
    ("codename-flood", "Project Falco Project Monsoo " * 70),
    ("prefix-flood", "sk-" + "a-" * 998),
], ids=["digit-run", "dash-digits", "long-number", "keyword-flood", "codename-flood", "prefix-flood"])
def test_JT28_latency_on_adversarial_input(name, text):
    """Pathological 2,000-char passages (regex backtracking / Luhn storms) stay under 20 ms and do not over-block."""
    text = text[:2000]
    ps = [P(f"a#{i}", text) for i in range(5)]
    ms = median_ms(lambda: adapter.check("anchor days?", ps), runs=15, warmup=2)
    assert ms < LIMIT_MS, f"{name}: median {ms:.2f} ms >= {LIMIT_MS} ms"
    if name in ("digit-run", "long-number", "keyword-flood", "codename-flood"):
        r = V(adapter.check("anchor days?", ps[:1]))
        assert r["dropped"] == [], f"{name}: over-blocked look-alike text {r['findings']}"
