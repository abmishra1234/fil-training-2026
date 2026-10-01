"""Every protected endpoint must validate the bearer token completely."""
import time

import pytest

from checks import assert_envelope
from harness import unsigned_token

cat = pytest.mark.cat


def probe(api, header_value=None, params=None):
    h = {"Authorization": header_value} if header_value is not None else {}
    return api.http.get("/api/v1/expenses", headers=h, params=params)


def assert_401(r):
    err = assert_envelope(r, 401, "not_authenticated")
    assert "bearer" in r.headers.get("www-authenticate", "").lower(), "401 must send WWW-Authenticate: Bearer"
    return err


@cat("TOKEN")
def test_token_01_missing_header(api):
    """TOKEN-01 No Authorization header -> 401 not_authenticated + WWW-Authenticate: Bearer"""
    assert_401(probe(api))


@cat("TOKEN")
@pytest.mark.parametrize("value", ["Bearer", "Basic YXNoYTpwYXNz", "Bearer abc", "Bearer a.b.c",
                                   "Bearer eyJhbGciOiJIUzI1NiJ9..", "Bearer " + "A" * 3000])
def test_token_02_malformed_header(api, value):
    """TOKEN-02 Malformed / wrong-scheme Authorization header -> 401"""
    assert_401(probe(api, value))


@cat("TOKEN")
def test_token_03_scheme_required(api):
    """TOKEN-03 A valid token without the 'Bearer' scheme is rejected"""
    assert_401(probe(api, api.token("asha")))
    assert_401(probe(api, "Token " + api.token("asha")))


@cat("TOKEN")
def test_token_04_valid_minted_token_accepted(api):
    """TOKEN-04 A correctly signed token (JWT_SECRET, HS256, iss) is accepted -> 200"""
    r = probe(api, "Bearer " + api.mint({"sub": "1"}))
    assert r.status_code == 200, r.text[:200]


@cat("TOKEN")
def test_token_05_tampered_payload(api):
    """TOKEN-05 Payload changed (sub -> finance admin) but old signature kept -> 401"""
    real = api.token("asha").split(".")
    forged_payload = api.mint({"sub": "6"}).split(".")[1]
    assert_401(probe(api, f"Bearer {real[0]}.{forged_payload}.{real[2]}"))


@cat("TOKEN")
def test_token_06_tampered_signature(api):
    """TOKEN-06 Signature altered by one character -> 401"""
    t = api.token("asha")
    last = t[-2]
    flipped = t[:-2] + ("A" if last != "A" else "B") + t[-1]
    assert_401(probe(api, "Bearer " + flipped))


@cat("TOKEN")
@pytest.mark.parametrize("alg", ["none", "None", "NONE", "nOnE"])
def test_token_07_alg_none(api, alg):
    """TOKEN-07 Unsigned token (alg=none) -> 401"""
    now = int(time.time())
    tok = unsigned_token({"sub": "6", "iss": "expense-api", "iat": now, "exp": now + 600}, alg)
    assert_401(probe(api, "Bearer " + tok))


@cat("TOKEN")
def test_token_08_wrong_secret(api):
    """TOKEN-08 Token signed with a different secret -> 401"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": "6"}, secret="another-secret-that-is-long-enough-123")))


@cat("TOKEN")
@pytest.mark.parametrize("alg", ["HS384", "HS512"])
def test_token_09_algorithm_pinned(api, alg):
    """TOKEN-09 Only HS256 is accepted (algorithm pinned server-side)"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": "1"}, alg=alg)))


@cat("TOKEN")
def test_token_10_expired(api):
    """TOKEN-10 Expired token (exp 2 minutes ago) -> 401"""
    now = int(time.time())
    assert_401(probe(api, "Bearer " + api.mint({"sub": "1", "iat": now - 1000, "exp": now - 120})))


@cat("TOKEN")
@pytest.mark.parametrize("claim", ["exp", "iat", "sub", "iss"])
def test_token_11_required_claims(api, claim):
    """TOKEN-11 Token missing a required claim (exp/iat/sub/iss) -> 401"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": "1"}, drop=(claim,))))


@cat("TOKEN")
@pytest.mark.parametrize("iss", ["other-service", "EXPENSE-API", ""])
def test_token_12_wrong_issuer(api, iss):
    """TOKEN-12 Token from another issuer -> 401"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": "1", "iss": iss})))


@cat("TOKEN")
@pytest.mark.parametrize("sub", ["999", "0", "asha", "-1", "1 OR 1=1", ""])
def test_token_13_unknown_or_bad_subject(api, sub):
    """TOKEN-13 Correctly signed token for a non-existent / malformed subject -> 401"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": sub})))


@cat("TOKEN")
def test_token_14_disabled_user(api):
    """TOKEN-14 Correctly signed token for a DISABLED user (dinesh) -> 401"""
    assert_401(probe(api, "Bearer " + api.mint({"sub": "8"})))


@cat("TOKEN")
def test_token_15_future_iat(api):
    """TOKEN-15 Token issued in the future (iat = now + 1 h) -> 401"""
    now = int(time.time())
    assert_401(probe(api, "Bearer " + api.mint({"sub": "1", "iat": now + 3600, "exp": now + 4000})))


@cat("TOKEN")
def test_token_16_token_in_query_string_not_accepted(api):
    """TOKEN-16 Tokens are only read from the header, never from the URL"""
    assert_401(probe(api, None, params={"access_token": api.token("asha")}))
    assert_401(probe(api, None, params={"token": api.token("asha")}))


@cat("TOKEN")
def test_token_17_all_failures_look_the_same(api):
    """TOKEN-17 Every token failure returns the same code + message (no oracle)"""
    now = int(time.time())
    variants = [None, "Bearer abc", "Bearer " + api.mint({"sub": "1", "exp": now - 60, "iat": now - 900}),
                "Bearer " + api.mint({"sub": "8"}), "Bearer " + api.mint({"sub": "1"}, secret="x" * 40)]
    sigs = set()
    for v in variants:
        e = probe(api, v).json()["error"]
        sigs.add((e["code"], e["message"]))
    assert len(sigs) == 1, f"different 401 bodies reveal which check failed: {sigs}"


@cat("TOKEN")
def test_token_18_decision_endpoint_requires_auth_first(api):
    """TOKEN-18 Decision endpoint: no token -> 401 even for unknown ids / bad bodies"""
    for eid in ("1001", "9999", "abc"):
        r = api.http.post(f"/api/v1/expenses/{eid}/decision", json={"decision": "APPROVE"},
                          headers={"Idempotency-Key": "judge-noauth-0001"})
        assert_401(r)


@cat("RBAC")
def test_rbac_01_role_claim_in_token_is_not_trusted(api):
    """RBAC-01 A 'role: FINANCE_ADMIN' claim in asha's token must NOT widen her access"""
    tok = api.mint({"sub": "1", "role": "FINANCE_ADMIN", "roles": ["FINANCE_ADMIN", "MANAGER"]})
    r = probe(api, "Bearer " + tok, params={"page_size": "100"})
    assert r.status_code == 200
    assert r.json()["total"] == 8, "role must come from the user store, not from the token"
    d = api.http.post("/api/v1/expenses/1007/decision", json={"decision": "APPROVE"},
                      headers={"Authorization": "Bearer " + tok, "Idempotency-Key": "judge-role-claim-1"})
    assert_envelope(d, 403, "forbidden")
