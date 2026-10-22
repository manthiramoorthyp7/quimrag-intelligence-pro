"""FastAPI application entrypoint.

Run with:  .venv/bin/uvicorn backend.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .db import SessionLocal, init_db
from .ingestion import rebuild_index_from_storage
from .routers import ask, documents, system, verify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("quimrag.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized at %s", config.DATABASE_URL)
    logger.info("Auth enabled: %s", config.AUTH_ENABLED)
    db = SessionLocal()
    try:
        result = rebuild_index_from_storage(db)
        logger.info("Startup index rebuild: %s", result)
    finally:
        db.close()
    yield


app = FastAPI(
    title="QuIM-RAG Intelligence Pro API",
    description="Document intelligence platform backend: ingestion, hybrid retrieval, "
                 "Evidence-Adaptive Retrieval & Verification (EAR), citation-verified generation, and "
                 "on-demand claim-level Evidence Integrity & Counterfactual Verification (EICV).",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Local-dev-only wildcard regex (any localhost/127.0.0.1 port) -- this
    # backend has no auth by default on the single-machine target
    # (ARCHITECTURE_DECISIONS.md #6), so this is not loosening a real
    # security boundary; tighten to explicit origins before exposing the
    # API beyond localhost.
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Phase 8: "Do not expose internal stack traces or secrets to clients."
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(system.router)
app.include_router(documents.router)
app.include_router(ask.router)
app.include_router(verify.router)
