"""Task 1 - Path-based versioning with zero breaking changes."""


def test_legacy_path_still_works(client):
    r = client.post("/accounts/", json={"owner_name": "Legacy Client"})
    assert r.status_code == 200
    acc_id = r.json()["id"]
    assert client.get(f"/accounts/{acc_id}").status_code == 200


def test_v1_path_works(client):
    r = client.post("/api/v1/accounts/", json={"owner_name": "V1 Client"})
    assert r.status_code == 200
    acc_id = r.json()["id"]
    assert client.get(f"/api/v1/accounts/{acc_id}").json()["owner_name"] == "V1 Client"


def test_both_paths_hit_the_same_data(client):
    acc_id = client.post("/accounts/", json={"owner_name": "Shared"}).json()["id"]
    client.post(f"/api/v1/accounts/{acc_id}/deposit", json={"amount": 100})
    assert client.get(f"/accounts/{acc_id}").json()["balance"] == 100


def test_all_existing_endpoints_exposed_under_v1(client):
    paths = set(client.get("/openapi.json").json()["paths"])
    for legacy in ["/accounts/", "/accounts/transfer", "/accounts/{account_id}",
                   "/accounts/{account_id}/deposit", "/accounts/{account_id}/withdraw",
                   "/accounts/{account_id}/kyc-status"]:
        assert legacy in paths, f"legacy route removed: {legacy}"
        assert "/api/v1" + legacy in paths, f"missing v1 route: /api/v1{legacy}"


def test_part_b_legacy_responses_carry_deprecation_headers(client):
    r = client.get("/accounts/")
    assert "Deprecation" in r.headers
    assert "Sunset" in r.headers
    assert "/api/v1/accounts/" in r.headers.get("Link", "")
    assert "Deprecation" not in client.get("/api/v1/accounts/").headers
