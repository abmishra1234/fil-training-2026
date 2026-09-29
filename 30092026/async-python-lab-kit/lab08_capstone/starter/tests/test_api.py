import time

from fastapi.testclient import TestClient

from app.main import app


def wait_for_final_status(client: TestClient, transfer_id: str, timeout: float = 5.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/transfers/{transfer_id}").json()
        if body["notification_status"] not in ("QUEUED", "SENDING"):
            return body
        time.sleep(0.05)
    raise AssertionError(f"notification for {transfer_id} never finished")


def test_transfer_is_accepted_fast_and_notified_later():
    with TestClient(app) as client:            # 'with' runs the lifespan -> workers start
        t0 = time.perf_counter()
        r = client.post("/transfers", json={"from_account": "ACC-101", "to_account": "ACC-102", "amount": 1500})
        assert r.status_code == 202
        assert time.perf_counter() - t0 < 0.5  # did not wait for notifications
        body = wait_for_final_status(client, r.json()["transfer_id"])
        assert body["notification_status"] == "SENT"
        assert client.get("/accounts/ACC-101").json()["balance"] == 48_500


def test_sms_failure_is_reported_not_crashed():
    with TestClient(app) as client:
        r = client.post("/transfers", json={"from_account": "ACC-103", "to_account": "ACC-101", "amount": 100})
        body = wait_for_final_status(client, r.json()["transfer_id"])
        assert body["notification_status"] == "PARTIAL_FAILURE"
        assert body["channels"]["email"] == "SENT"


def test_business_and_validation_errors():
    with TestClient(app) as client:
        assert client.post("/transfers", json={"from_account": "ACC-102", "to_account": "ACC-101",
                                               "amount": 999_999}).status_code == 400
        assert client.post("/transfers", json={"from_account": "ACC-101", "to_account": "ACC-102",
                                               "amount": -1}).status_code == 422
        assert client.get("/transfers/TXN-NOPE").status_code == 404
