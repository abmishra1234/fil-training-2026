from fastapi import FastAPI, HTTPException # pyright: ignore[reportMissingImports]
import time
from collections import deque

app = FastAPI(title="A04 Insecure Design - Secure")

WINDOW = 60  # seconds
LIMIT = 5    # attempts per window per user
buckets: dict[str, deque] = {}

def allow(user_id: str) -> bool:
    now = time.time()
    dq = buckets.setdefault(user_id, deque())
    while dq and now - dq[0] > WINDOW:
        dq.popleft()
    if len(dq) >= LIMIT:
        return False
    dq.append(now)
    return True

@app.post("/login")
async def login(user: str, password: str):
    if not allow(user):
        raise HTTPException(429, "Too many attempts")
    return {"user": user, "ok": (password == "secret")}
