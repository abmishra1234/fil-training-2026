"""Ext 6 - Task 6: role-based access control (RBAC)."""


def test_customer_cannot_self_certify_kyc(client, make_account):
    acc = make_account("Self Certifier")
    r = client.put(f"/api/v1/accounts/{acc}/kyc-status", json={"kyc_compliant": True})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
    assert client.get(f"/api/v1/accounts/{acc}/kyc-status").json()["kyc_compliant"] is False


def test_admin_can_certify_kyc(client, admin_headers, make_account):
    acc = make_account("Needs KYC")
    r = client.put(f"/api/v1/accounts/{acc}/kyc-status", json={"kyc_compliant": True},
                   headers=admin_headers)
    assert r.status_code == 200 and r.json()["kyc_compliant"] is True


def test_admin_sees_all_accounts(anon_client, admin_headers, login, make_account):
    acc = make_account("Anyone", headers=login("rbac.cust"))
    ids = [a["id"] for a in anon_client.get("/api/v1/accounts/", headers=admin_headers).json()]
    assert acc in ids


def test_admin_can_view_but_not_move_customer_money(anon_client, admin_headers, make_account):
    acc = make_account("Protected Funds", balance=100)
    assert anon_client.get(f"/api/v1/accounts/{acc}", headers=admin_headers).status_code == 200
    r = anon_client.post(f"/api/v1/accounts/{acc}/withdraw", json={"amount": 50}, headers=admin_headers)
    assert r.status_code == 403                               # least privilege


def test_admin_endpoints_reject_customers(anon_client, login):
    r = anon_client.get("/api/v1/admin/users", headers=login("nosy.customer"))
    assert r.status_code == 403


def test_admin_can_list_users_without_hashes(anon_client, admin_headers):
    r = anon_client.get("/api/v1/admin/users", headers=admin_headers)
    assert r.status_code == 200
    assert any(u["role"] == "ADMIN" for u in r.json())
    assert "hashed_password" not in r.text


def test_deactivated_user_is_locked_out_immediately(anon_client, admin_headers, login):
    h = login("soon.disabled")
    uid = anon_client.get("/api/v1/auth/me", headers=h).json()["id"]
    r = anon_client.patch(f"/api/v1/admin/users/{uid}", json={"is_active": False}, headers=admin_headers)
    assert r.status_code == 200 and r.json()["is_active"] is False
    # Same, still-unexpired token -> now rejected, because get_current_user re-checks the DB.
    assert anon_client.get("/api/v1/auth/me", headers=h).status_code == 401
