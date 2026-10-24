"""
Group B - Credentials and API keys: known key prefixes, and password / secret / api_key
followed by = or :.                                                                  JT08 - JT11
"""
from __future__ import annotations

from pathlib import Path

import adapter
import pytest
from samples import AKIA_KEY, CLIENT_SECRET, PASSWORD_ASSIGN, SK_KEY, SK_LIVE

P = adapter.make_passage
V = adapter.result_view
ROOT = Path(__file__).resolve().parent.parent


def cred_count(text: str) -> int:
    r = V(adapter.check("q", [P("t#0", text)]))
    return r["findings"].get(adapter.TYPE_CREDENTIAL, 0)


@pytest.mark.parametrize("key", [SK_KEY, SK_LIVE, "sk-proj-AbCdEf0123456789XyZ", AKIA_KEY],
                         ids=["sk-test", "sk-live", "sk-proj", "AKIA"])
def test_JT08_known_key_prefixes_in_passage_and_query(key):
    """Known key prefixes are credentials wherever they appear: mid-sentence, quoted, end of line."""
    for text in (f"use {key} for staging", f'"{key}"', f"key={key}", f"(see {key}).", key):
        r = V(adapter.check("q", [P("k#0", text), P("k#1", "clean")]))
        assert r["dropped"] == ["k#0"], f"not detected in: {text!r}"
        assert r["findings"].get(adapter.TYPE_CREDENTIAL, 0) >= 1
    q = V(adapter.check(f"why is {key} rejected?", [P("k#2", "clean")]))
    assert q["decision"] == "BLOCK_QUERY"


@pytest.mark.parametrize("text", [
    PASSWORD_ASSIGN,
    CLIENT_SECRET,
    "api_key=abc123XYZ987",
    "Password: Summer#2025",
    "API_KEY = 9f8e7d6c",
    "secret:hunter22",
    "DB_PASSWORD=Tr0ub4dor&3",
    "SECRET = 'rotate-me-0042'",
], ids=["password=", "client_secret:", "api_key=", "Password:", "API_KEY =", "secret:", "DB_PASSWORD=", "SECRET ="])
def test_JT09_keyword_assignments_are_credentials(text):
    """password / secret / api_key followed by = or : (any case, optional spaces, optional NAME_ prefix)."""
    sentence = f"Config dump from the runbook: {text} (temporary)."
    assert cred_count(sentence) == 1, f"expected exactly 1 credential in {sentence!r}"


def test_JT10_no_false_positives_on_policy_text_and_the_real_handbook():
    """Talking ABOUT passwords and keys is not a secret. The whole handbook corpus must pass clean."""
    clean = [
        "API keys, client secrets, passwords and tokens must never be committed to git.",
        "Use the secrets manager VaultNova; a leaked secret must be reported within 1 hour.",
        "Passwords must be at least 14 characters long and are not force-rotated.",
        "The risk-based review covers desk-booking and task-tracking tools.",
        "We use sk-learn for models; the AKIA prefix is explained in the AWS guide.",
        "The secret to good reviews is preparation. Rotate the api_key quarterly.",
        "Password policy and secrets handling are covered in 08_security_passwords.md",
    ]
    r = V(adapter.check("password policy?", [P(f"c#{i}", t) for i, t in enumerate(clean)]))
    assert r["decision"] == "ALLOW" and r["dropped"] == [], f"false positives: {r['dropped']}"

    from app.ingest import load_folder

    chunks = load_folder(ROOT / "data" / "docs", 500, 60)
    assert len(chunks) > 20, "the handbook corpus (data/docs) is missing"
    ps = [P(d.metadata["chunk_id"], d.page_content) for d in chunks]
    r = V(adapter.check("anything", ps))
    assert r["dropped"] == [], f"handbook chunks wrongly flagged: {r['dropped']} {r['findings']}"
    assert r["decision"] == "ALLOW"


def test_JT11_counts_every_distinct_credential_once():
    """Three different credentials in one passage count as 3 (not 1, not double-counted)."""
    text = f"Staging uses {SK_KEY}.\nAWS: {AKIA_KEY}\nDB {PASSWORD_ASSIGN}\nnothing else here"
    assert cred_count(text) == 3
    assert cred_count(f"{SK_KEY} {SK_KEY}") == 2, "the same key twice is two occurrences"
