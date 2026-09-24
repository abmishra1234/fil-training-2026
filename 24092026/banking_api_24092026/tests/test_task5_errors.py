"""Task 5 - One error format for /api/v1, legacy contract untouched."""


def assert_envelope(r, status, code):
    assert r.status_code == status, r.text
    err = r.json()["error"]
    assert err["code"] == code
    assert isinstance(err["message"], str) and err["message"]
    assert isinstance(err["details"], dict)
    assert err["request_id"] == r.headers["X-Request-ID"]
    return err


def test_insufficient_funds_v1(client, make_account):
    acc = make_account("Low", balance=54.2)
    r = client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 100})
    err = assert_envelope(r, 400, "insufficient_funds")
    assert err["details"] == {"current_balance": 54.2, "requested_amount": 100}


def test_insufficient_funds_legacy_unchanged(client, make_account):
    acc = make_account("Low2", balance=10)
    r = client.post(f"/accounts/{acc}/withdraw", json={"amount": 100})
    assert r.status_code == 400
    assert r.json() == {"detail": "Insufficient funds"}


def test_not_found_v1_and_legacy(client):
    # Ext 6: the ownership check (AccountAccess) now runs first and raises the
    # domain error, so the code is the more specific 'account_not_found'.
    assert_envelope(client.get("/api/v1/accounts/999999"), 404, "account_not_found")
    assert client.get("/accounts/999999").json() == {"detail": "Account not found"}


def test_validation_error_v1_lists_fields(client):
    r = client.post("/api/v1/accounts/", json={})
    err = assert_envelope(r, 422, "validation_error")
    assert any("owner_name" in f["field"] for f in err["details"]["fields"])


def test_validation_error_legacy_unchanged(client):
    r = client.post("/accounts/", json={})
    assert r.status_code == 422 and "detail" in r.json()


def test_domain_errors_from_new_endpoints(client, make_account):
    assert_envelope(client.get("/api/v1/accounts/999999/transactions"), 404, "account_not_found")
    acc = make_account("S")
    assert_envelope(client.get(f"/api/v1/accounts/{acc}/transactions",
                               params={"sort_by": "hack"}), 400, "invalid_request")


def test_unknown_v1_route_uses_envelope(client):
    assert_envelope(client.get("/api/v1/does-not-exist"), 404, "not_found")


def test_client_supplied_request_id_is_echoed(client):
    r = client.get("/api/v1/accounts/999999", headers={"X-Request-ID": "trace-abc-123"})
    assert r.headers["X-Request-ID"] == "trace-abc-123"
    assert r.json()["error"]["request_id"] == "trace-abc-123"


def test_unhandled_exception_is_500_without_stack_trace(client):
    from app.main import app

    @app.get("/api/v1/_boom")
    def boom():
        raise RuntimeError("secret db password in stack trace")

    r = client.get("/api/v1/_boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret" not in r.text
