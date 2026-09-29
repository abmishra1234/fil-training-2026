"""Lab 7 - FastAPI Banking API: async endpoints + BackgroundTasks

Run:   fastapi dev main.py            (fallback: python -m uvicorn main:app --reload)
Open:  http://127.0.0.1:8000/docs     (Swagger UI - try POST /transfers there)

PART A  (BackgroundTasks)  - the endpoint returns 202 immediately; notifications
                             are sent AFTER the response. Watch the server terminal.
PART B  (experiment)       - three 'slow' endpoints; run  python load_test.py
                             to see which one freezes the whole server.
"""
import asyncio
import time
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="FIL Training - Mini Bank")

ACCOUNTS: dict[str, float] = {"ACC-101": 50_000.0, "ACC-102": 12_000.0, "ACC-103": 800.0}
NOTIFICATION_LOG: list[str] = []


def log(msg: str) -> None:
    print(f"{datetime.now():%H:%M:%S.%f}"[:-3], msg, flush=True)


class TransferRequest(BaseModel):
    from_account: str = Field(examples=["ACC-101"])
    to_account: str = Field(examples=["ACC-102"])
    amount: float = Field(gt=0, le=1_000_000, examples=[1500.0])


class TransferAccepted(BaseModel):
    transfer_id: str
    status: str
    message: str


# ---------------- PART A: BackgroundTasks ----------------
async def send_notifications(transfer_id: str, req: TransferRequest) -> None:
    """Runs AFTER the HTTP response has been sent."""
    log(f"[bg] {transfer_id}: sending email + SMS ...")
    await asyncio.gather(asyncio.sleep(2), asyncio.sleep(3))  # email (2 s) and SMS (3 s) in parallel
    NOTIFICATION_LOG.append(transfer_id)
    log(f"[bg] {transfer_id}: notifications sent for INR {req.amount:,.2f}")


@app.post("/transfers", status_code=status.HTTP_202_ACCEPTED, response_model=TransferAccepted)
async def create_transfer(req: TransferRequest, background_tasks: BackgroundTasks) -> TransferAccepted:
    # 1. critical, fast business logic - must finish before we answer
    if req.from_account not in ACCOUNTS or req.to_account not in ACCOUNTS:
        raise HTTPException(status_code=404, detail="account not found")
    if req.from_account == req.to_account:
        raise HTTPException(status_code=400, detail="cannot transfer to same account")
    if ACCOUNTS[req.from_account] < req.amount:
        raise HTTPException(status_code=400, detail="insufficient funds")
    ACCOUNTS[req.from_account] -= req.amount
    ACCOUNTS[req.to_account] += req.amount
    transfer_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
    log(f"[api] {transfer_id}: money moved, responding now")

    # 2. non-critical, slow work -> runs after the response is sent
    background_tasks.add_task(send_notifications, transfer_id, req)
    return TransferAccepted(transfer_id=transfer_id, status="ACCEPTED",
                            message="Transfer done. Notification will follow shortly.")


@app.get("/accounts/{account_id}")
async def get_account(account_id: str) -> dict:
    if account_id not in ACCOUNTS:
        raise HTTPException(status_code=404, detail="account not found")
    return {"account": account_id, "balance": ACCOUNTS[account_id],
            "as_of": datetime.now(timezone.utc).isoformat()}


# ---------------- PART B: def vs async def experiment ----------------
@app.get("/slow/async-blocking")
async def slow_async_blocking() -> dict:
    time.sleep(1)            # BAD: blocks the event loop -> every other request waits
    return {"endpoint": "async-blocking"}


@app.get("/slow/sync-def")
def slow_sync_def() -> dict:
    time.sleep(1)            # OK: plain 'def' endpoints run in FastAPI's thread pool
    return {"endpoint": "sync-def"}


@app.get("/slow/async-nonblocking")
async def slow_async_nonblocking() -> dict:
    await asyncio.sleep(1)   # BEST for I/O: non-blocking await
    return {"endpoint": "async-nonblocking"}
