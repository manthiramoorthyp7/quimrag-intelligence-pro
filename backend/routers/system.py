"""Health/readiness + a real system-info endpoint (Phase 3's Command Center
needs actual backend data, not placeholders) -- hardware/device, model
status, and index size, all read live from the running engine."""
import os

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import Depends

from quimrag.local_llm import ollama_available

from .. import config
from ..db import get_db
from ..engine_singleton import get_ear_model, get_engine
from ..models import Document
from ..schemas import HealthOut

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
def health():
    engine = get_engine()
    ear_loaded = os.path.exists(config.EAR_CALIBRATION_PATH)
    get_ear_model()  # touches the lazy loader so the status above is accurate post-first-call too
    return HealthOut(
        status="ok",
        device=engine.dev,
        embedding_backend=engine.backend,
        reranker_loaded=engine.reranker is not None,
        documents_indexed=len(engine.documents),
        chunks_indexed=len(engine.chunks),
        ollama_available=ollama_available(),
        ear_calibration_loaded=ear_loaded,
        auth_enabled=config.AUTH_ENABLED,
        database_url_scheme=config.DATABASE_URL.split(":")[0],
    )


@router.get("/system/stats")
def system_stats(db: Session = Depends(get_db)):
    """Real counts for the Command Center -- no hardcoded demo numbers."""
    total = db.execute(select(func.count()).select_from(Document).where(Document.status != "deleted")).scalar()
    ready = db.execute(select(func.count()).select_from(Document).where(Document.status == "ready")).scalar()
    processing = db.execute(select(func.count()).select_from(Document).where(Document.status == "processing")).scalar()
    failed = db.execute(select(func.count()).select_from(Document).where(Document.status == "failed")).scalar()
    return {
        "documents_total": total, "documents_ready": ready,
        "documents_processing": processing, "documents_failed": failed,
    }
