"""Ext 6 - Task 4: no money endpoint is reachable without a token."""
import pytest

PROTECTED = [
    ("get", "/api/v1/accounts/"),
    ("post", "/api/v1/accounts/"),
    ("get", "/api/v1/accounts/1"),
    ("post", "/api/v1/accounts/1/deposit"),
    ("post", "/api/v1/accounts/1/withdraw"),
    ("post", "/api/v1/accounts/transfer"),
    ("get", "/api/v1/accounts/1/kyc-status"),
    ("put", "/api/v1/accounts/1/kyc-status"),
    ("get", "/api/v1/accounts/1/transactions"),
    ("get", "/api/v1/accounts/1/scheduled-payments"),
    ("post", "/api/v1/accounts/1/scheduled-payments"),
    ("get", "/api/v1/scheduled-payments/1"),
    ("patch", "/api/v1/scheduled-payments/1"),
    ("delete", "/api/v1/scheduled-payments/1"),
    ("get", "/api/v1/admin/users"),
    ("get", "/accounts/"),                      # legacy door must be locked too
    ("post", "/accounts/1/withdraw"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_route_requires_token(anon_client, method, path):
    r = getattr(anon_client, method)(path)
    assert r.status_code == 401, f"{method.upper()} {path} is NOT protected"
    assert r.headers.get("WWW-Authenticate") == "Bearer"


@pytest.mark.parametrize("path", ["/", "/docs", "/openapi.json"])
def test_public_routes_stay_public(anon_client, path):
    assert anon_client.get(path).status_code == 200


def test_openapi_advertises_bearer_security(anon_client):
    schemes = anon_client.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(s.get("type") == "oauth2" for s in schemes.values())
