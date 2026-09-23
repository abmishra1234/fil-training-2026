from fastapi import FastAPI # type: ignore
app = FastAPI(title="A04 Insecure Design - Insecure")

# No rate limiting, brute-force possible
@app.post("/login")
async def login(user: str, password: str):
    return {"user": user, "ok": (password == "secret")}
