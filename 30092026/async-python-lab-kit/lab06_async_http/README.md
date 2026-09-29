# Lab 6 - Async HTTP with httpx2 (30 min)

Terminal 1 (leave running):
```
fastapi dev mock_bank_api.py --port 8001
```
Terminal 2:
```
python client_sync.py     # ~6 s
python starter.py         # your work
python solution.py        # ~2 s (Semaphore 3); remove the semaphore -> ~1 s
```
Why a local mock server? Corporate networks/proxies make public APIs unreliable in class,
and a local server gives everybody the same, predictable latency.

Rules: one `AsyncClient` per app (connection pooling), always set `timeout`,
`raise_for_status()`, catch `httpx2.HTTPStatusError` (bad status) and `httpx2.RequestError` (network).
Note: `requests` is sync-only - never call it inside `async def`.

**httpx vs httpx2:** `httpx2` is the next-generation successor of `httpx` by the same author
(now maintained by Pydantic); the API used here is identical and Starlette/FastAPI's
`TestClient` now prefers it. It also uses your OS certificate store (truststore), which
helps behind corporate SSL-inspecting proxies. Existing projects on `httpx` 0.28 can use
the same code with `import httpx`.
