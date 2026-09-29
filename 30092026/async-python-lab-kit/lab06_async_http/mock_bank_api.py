"""Mock 'partner bank' FX-rate API (no internet needed - runs on your laptop).

Start it in its own terminal and leave it running:
    fastapi dev mock_bank_api.py --port 8001
    (fallback:  python -m uvicorn mock_bank_api:app --port 8001)
Try it:  http://127.0.0.1:8001/docs
"""
import asyncio
import random

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Mock Partner Bank API")

RATES = {"USD": 83.2, "EUR": 90.1, "GBP": 105.4, "JPY": 0.56, "SGD": 61.9, "AED": 22.7}


@app.get("/fx/{currency}")
async def fx_rate(currency: str, delay: float = 1.0) -> dict:
    await asyncio.sleep(delay)  # simulated network + processing latency
    code = currency.upper()
    if code not in RATES:
        raise HTTPException(status_code=404, detail=f"unknown currency {code}")
    return {"currency": code, "inr": RATES[code]}


@app.get("/flaky")
async def flaky() -> dict:
    await asyncio.sleep(0.2)
    if random.random() < 0.5:
        raise HTTPException(status_code=503, detail="partner temporarily unavailable")
    return {"status": "ok"}
