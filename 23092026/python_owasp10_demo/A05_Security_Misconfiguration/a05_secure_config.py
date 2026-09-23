from fastapi import FastAPI # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore

# Secure: Debug disabled; strict CORS and headers applied via middleware
app = FastAPI(title="A05 Security Misconfiguration - Secure", debug=False)

ALLOWED_ORIGINS = ["https://example.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}
