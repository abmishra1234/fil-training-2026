from fastapi import FastAPI # type: ignore

# Insecure: Debug mode enabled (not recommended for production)
app = FastAPI(title="A05 Security Misconfiguration - Insecure", debug=True)

@app.get("/")
def read_root():
    1 / 0  # Force an error to demonstrate stack trace behavior
    return {"Hello": "World"}
