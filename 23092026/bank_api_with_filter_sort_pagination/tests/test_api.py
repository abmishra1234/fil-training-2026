from collections.abc import Generator
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, engine, get_db
from app.main import app
from app.models.transfer_history import TransferHistory


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    """Provide a client backed by a fresh SQLite database for each test."""
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        database_session = test_session()
        try:
            yield database_session
        finally:
            database_session.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.session_factory = test_session
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_account(client: TestClient, owner_name: str, balance: float = 0.0) -> dict:
    response = client.post(
        "/accounts/", json={"owner_name": owner_name, "balance": balance}
    )
    assert response.status_code == 201
    return response.json()


def test_root_returns_welcome_message(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to the Personal Banking API"


def test_versioned_api_exposes_every_current_endpoint(client: TestClient) -> None:
    current_paths = {
        path: methods
        for path, methods in app.openapi()["paths"].items()
        if path == "/" or path.startswith("/accounts")
    }

    assert client.get("/api/v1").json() == client.get("/").json()
    for path, methods in current_paths.items():
        versioned_path = "/api/v1" if path == "/" else f"/api/v1{path}"
        assert app.openapi()["paths"][versioned_path].keys() == methods.keys()


def test_versioned_and_current_paths_share_the_same_api(client: TestClient) -> None:
    account = client.post(
        "/api/v1/accounts/", json={"owner_name": "Asha", "balance": 100}
    )

    assert account.status_code == 201
    response = client.get(f"/accounts/{account.json()['id']}")
    assert response.status_code == 200
    assert response.json() == account.json()


def test_create_account_uses_supplied_balance(client: TestClient) -> None:
    account = create_account(client, "Asha", 125.50)

    assert account["owner_name"] == "Asha"
    assert account["balance"] == 125.50


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"owner_name": "Al"}, "owner_name"),
        ({"owner_name": "A" * 51}, "owner_name"),
        ({"owner_name": "Asha", "balance": -1}, "balance"),
    ],
)
def test_create_account_rejects_invalid_input(
    client: TestClient, payload: dict, field: str
) -> None:
    response = client.post("/accounts/", json=payload)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_list_accounts_and_get_account(client: TestClient) -> None:
    account = create_account(client, "Asha", 50)

    list_response = client.get("/accounts/")
    get_response = client.get(f"/accounts/{account['id']}")

    assert list_response.status_code == 200
    assert list_response.json() == [account]
    assert get_response.status_code == 200
    assert get_response.json() == account


def test_get_unknown_account_returns_404(client: TestClient) -> None:
    response = client.get("/accounts/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Account not found"}


def test_deposit_updates_balance(client: TestClient) -> None:
    account = create_account(client, "Asha", 100)

    response = client.post(f"/accounts/{account['id']}/deposit", json={"amount": 25})

    assert response.status_code == 200
    assert response.json()["balance"] == 125


@pytest.mark.parametrize("amount", [0, -10])
def test_deposit_requires_a_positive_amount(client: TestClient, amount: float) -> None:
    account = create_account(client, "Asha", 100)

    response = client.post(f"/accounts/{account['id']}/deposit", json={"amount": amount})

    assert response.status_code == 400
    assert response.json() == {"detail": "Deposit amount must be positive"}


def test_deposit_to_unknown_account_returns_404(client: TestClient) -> None:
    response = client.post("/accounts/999/deposit", json={"amount": 10})

    assert response.status_code == 404


def test_withdraw_updates_balance(client: TestClient) -> None:
    account = create_account(client, "Asha", 100)

    response = client.post(f"/accounts/{account['id']}/withdraw", json={"amount": 40})

    assert response.status_code == 200
    assert response.json()["balance"] == 60


@pytest.mark.parametrize(
    ("amount", "message"),
    [(0, "Withdraw amount must be positive"), (150, "Insufficient funds")],
)
def test_withdraw_rejects_invalid_requests(
    client: TestClient, amount: float, message: str
) -> None:
    account = create_account(client, "Asha", 100)

    response = client.post(f"/accounts/{account['id']}/withdraw", json={"amount": amount})

    assert response.status_code == 400
    assert response.json() == {"detail": message}


def test_withdraw_from_unknown_account_returns_404(client: TestClient) -> None:
    response = client.post("/accounts/999/withdraw", json={"amount": 10})

    assert response.status_code == 404


def test_transfer_moves_money_between_accounts(client: TestClient) -> None:
    source = create_account(client, "Asha", 1000)
    destination = create_account(client, "Ravi", 50)

    response = client.post(
        "/accounts/transfer",
        json={
            "from_account_id": source["id"],
            "to_account_id": destination["id"],
            "amount": 300,
        },
    )

    assert response.status_code == 200
    assert response.json()["from_account"]["balance"] == 700
    assert response.json()["to_account"]["balance"] == 350

    with client.session_factory() as database_session:
        history = database_session.query(TransferHistory).one()

    assert history.from_account_id == source["id"]
    assert history.to_account_id == destination["id"]
    assert history.amount == 300
    assert history.transfer_status == "SUCCESS"
    assert history.timestamp is not None


def test_list_transfers_returns_history_newest_first(client: TestClient) -> None:
    source = create_account(client, "Asha", 1000)
    first_destination = create_account(client, "Ravi", 0)
    second_destination = create_account(client, "Neha", 0)

    for destination, amount in ((first_destination, 100), (second_destination, 200)):
        response = client.post(
            "/accounts/transfer",
            json={
                "from_account_id": source["id"],
                "to_account_id": destination["id"],
                "amount": amount,
            },
        )
        assert response.status_code == 200

    response = client.get("/api/v1/accounts/transfers")

    assert response.status_code == 200
    assert [transfer["amount"] for transfer in response.json()] == [200, 100]
    assert response.json()[0]["transfer_status"] == "SUCCESS"


def test_transfer_history_stores_one_thousand_records(client: TestClient) -> None:
    source = create_account(client, "Asha", 1000)
    destination = create_account(client, "Ravi", 0)
    transfer_request = {
        "from_account_id": source["id"],
        "to_account_id": destination["id"],
        "amount": 1,
    }

    for _ in range(1000):
        response = client.post("/accounts/transfer", json=transfer_request)
        assert response.status_code == 200

    history_response = client.get("/accounts/transfers?page_size=1000")
    with client.session_factory() as database_session:
        history_count = database_session.query(TransferHistory).count()

    assert history_response.status_code == 200
    assert len(history_response.json()) == 1000
    assert history_count == 1000
    assert history_response.headers["X-Total-Count"] == "1000"
    assert history_response.json()[0]["amount"] == 1


@pytest.mark.bank_db
def test_bank_db_stores_one_thousand_verification_transfers() -> None:
    """Create retained verification data only when explicitly enabled."""
    if os.environ.get("RUN_BANK_DB_TESTS") != "1":
        pytest.skip("Set RUN_BANK_DB_TESTS=1 to write verification records to bank.db")

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as bank_client:
        source = bank_client.get("/accounts/1")
        destination = bank_client.get("/accounts/2")
        assert source.status_code == 200, "Account ID 1 must exist"
        assert destination.status_code == 200, "Account ID 2 must exist"
        assert source.json()["balance"] >= 1000, (
            "Account ID 1 needs a balance of at least 1000 to run this test"
        )
        history_filter = "from_account_id=1&to_account_id=2&page_size=1"
        initial_history = bank_client.get(f"/accounts/transfers?{history_filter}")
        assert initial_history.status_code == 200
        initial_matching_count = int(initial_history.headers["X-Total-Count"])
        transfer_request = {
            "from_account_id": 1,
            "to_account_id": 2,
            "amount": 1,
        }

        for _ in range(1000):
            response = bank_client.post("/accounts/transfer", json=transfer_request)
            assert response.status_code == 200

        history_response = bank_client.get(f"/accounts/transfers?{history_filter}")

    assert int(history_response.headers["X-Total-Count"]) == initial_matching_count + 1000


def test_transfer_history_supports_filters_sorting_and_pagination(
    client: TestClient,
) -> None:
    source = create_account(client, "Asha", 100)
    destination = create_account(client, "Ravi", 0)
    for amount in (5, 15, 25):
        response = client.post(
            "/accounts/transfer",
            json={
                "from_account_id": source["id"],
                "to_account_id": destination["id"],
                "amount": amount,
            },
        )
        assert response.status_code == 200

    response = client.get(
        "/accounts/transfers"
        f"?from_account_id={source['id']}&min_amount=10"
        "&sort_by=amount&sort_order=asc&page=2&page_size=1"
    )

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "2"
    assert response.headers["X-Total-Pages"] == "2"
    assert response.json()[0]["amount"] == 25


@pytest.mark.parametrize(
    ("from_id", "to_id", "amount", "status_code", "message"),
    [
        (1, 2, 0, 400, "Transfer amount must be positive"),
        (1, 1, 10, 400, "Cannot transfer to the same account"),
        (1, 999, 10, 404, "Account not found"),
        (1, 2, 500, 400, "Insufficient funds"),
    ],
)
def test_transfer_error_cases(
    client: TestClient,
    from_id: int,
    to_id: int,
    amount: float,
    status_code: int,
    message: str,
) -> None:
    source = create_account(client, "Asha", 100)
    destination = create_account(client, "Ravi", 0)
    account_ids = {1: source["id"], 2: destination["id"], 999: 999}

    response = client.post(
        "/accounts/transfer",
        json={
            "from_account_id": account_ids[from_id],
            "to_account_id": account_ids[to_id],
            "amount": amount,
        },
    )

    assert response.status_code == status_code
    assert response.json() == {"detail": message}


def test_transfer_requires_all_request_fields(client: TestClient) -> None:
    response = client.post("/accounts/transfer", json={"from_account_id": 1, "amount": 10})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "to_account_id"]


def test_kyc_status_is_false_for_new_account(client: TestClient) -> None:
    account = create_account(client, "Asha")

    response = client.get(f"/accounts/{account['id']}/kyc-status")

    assert response.status_code == 200
    assert response.json() == {"account_id": account["id"], "kyc_compliant": False}


def test_kyc_status_update_accepts_default_query_and_body(client: TestClient) -> None:
    account = create_account(client, "Asha")
    url = f"/accounts/{account['id']}/kyc-status"

    assert client.put(url).json()["kyc_compliant"] is True
    assert client.put(f"{url}?kyc_compliant=false").json()["kyc_compliant"] is False
    assert client.put(url, json={"kyc_compliant": True}).json()["kyc_compliant"] is True
    assert client.put(f"{url}?kyc_compliant=false", json={}).json()["kyc_compliant"] is True
    response = client.put(f"{url}?kyc_compliant=false", json={"kyc_compliant": True})

    assert response.status_code == 200
    assert response.json()["kyc_compliant"] is True


def test_kyc_status_handles_invalid_and_unknown_accounts(client: TestClient) -> None:
    account = create_account(client, "Asha")

    invalid_query = client.put(
        f"/accounts/{account['id']}/kyc-status?kyc_compliant=maybe"
    )
    unknown_get = client.get("/accounts/999/kyc-status")
    unknown_put = client.put("/accounts/999/kyc-status")

    assert invalid_query.status_code == 422
    assert unknown_get.status_code == 404
    assert unknown_put.status_code == 404
