"""
app/main.py - FastAPI application. (PROVIDED - no TODOs here)

Run from the project folder (the one with llm_client.py and .env):

    uvicorn app.main:app --reload --port 8000

Then open http://127.0.0.1:8000  (frontend)  or  http://127.0.0.1:8000/docs  (Swagger)
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from llm_client import describe

from .config import config
from .image_service import AdComposeError
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ad_composer")

app = FastAPI(
    title="Ad Composer API",
    description="Model image + product image + marketing quote -> advertisement image (FIL AI cohort lab)",
    version="1.0.0",
)


@app.exception_handler(AdComposeError)
def _ad_error(_: Request, exc: AdComposeError) -> JSONResponse:
    log.warning("AdComposeError %s: %s", exc.status_code, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "hint": exc.hint})


@app.exception_handler(NotImplementedError)
def _todo(_: Request, exc: NotImplementedError) -> JSONResponse:
    # Starter code: unimplemented TODOs answer 501 with the TODO name, instead of a scary 500.
    return JSONResponse(status_code=501, content={"error": str(exc) or "Not implemented yet",
                                                  "hint": "Open the file named in the message and complete the TODO."})


@app.exception_handler(Exception)
def _unexpected(_: Request, exc: Exception) -> JSONResponse:
    # Last line of defence: never leak stack traces or secrets to the browser.
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"error": "Unexpected server error.",
                                                  "hint": "Check the uvicorn console for the stack trace."})


app.include_router(router)

# The frontend is plain HTML/CSS/JS - FastAPI serves it, so there is no CORS and no Node build.
app.mount("/", StaticFiles(directory=config.frontend_dir, html=True), name="frontend")

log.info("Ad Composer ready | %s | dry_run=%s", describe(), config.dry_run)
