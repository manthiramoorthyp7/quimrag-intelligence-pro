"""Document ingestion pipeline: validate -> hash -> store -> extract ->
chunk -> embed -> index -> mark ready. Implements Phase 4's required steps
against the existing, unmodified quimrag.core extraction/chunking/embedding
code -- this module is the part that previously did not exist (there was no
background processing, status tracking, or deletion-with-verification before
this session; see docs/production/INITIAL_AUDIT.md #8)."""
import hashlib
import logging
import os
import time

from sqlalchemy.orm import Session

from quimrag.core import extract_pdf

from . import config
from .engine_singleton import ENGINE_LOCK, get_engine
from .models import AuditRecord, Document

logger = logging.getLogger("quimrag.ingestion")

PDF_MAGIC = b"%PDF-"


class ValidationError(Exception):
    pass


def validate_upload(filename: str, content: bytes) -> str:
    """Returns the normalized extension, or raises ValidationError. Checks
    the actual file content (magic bytes), not just the filename, to guard
    against MIME/extension spoofing per Phase 8's required checks."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise ValidationError(f"Unsupported file extension: {ext or '(none)'}")
    if len(content) == 0:
        raise ValidationError("Empty file")
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise ValidationError(f"File exceeds the {config.MAX_UPLOAD_BYTES} byte upload limit")
    if ext == ".pdf" and not content.startswith(PDF_MAGIC):
        raise ValidationError("File has a .pdf extension but does not start with the PDF magic bytes (%PDF-) -- "
                               "rejected as a possible extension/MIME spoofing attempt")
    return ext


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _pages_from_text_file(content: bytes) -> tuple[list[str], list[dict]]:
    text = content.decode("utf-8", errors="replace")
    return [text], [{"source": "native", "ocr_confidence": None}]


def _pages_from_pdf(content: bytes) -> tuple[list[str], list[dict], list[str]]:
    pages, notes, meta = extract_pdf(content, ocr=True)
    return pages, meta, notes


def process_document(document_id: str, db: Session) -> None:
    """Runs synchronously inside a FastAPI BackgroundTask. Re-opens its own
    DB session (the request's session is closed by the time this runs) and
    acquires the engine lock for the whole add_document+reindex call, since
    that mutates shared in-process state (see engine_singleton.py)."""
    doc = db.get(Document, document_id)
    if doc is None:
        logger.error("process_document: document %s vanished before processing", document_id)
        return
    t0 = time.perf_counter()
    try:
        with open(doc.storage_path, "rb") as f:
            content = f.read()
        ext = os.path.splitext(doc.filename)[1].lower()
        notes: list[str] = []
        if ext == ".pdf":
            pages, meta, notes = _pages_from_pdf(content)
        else:
            pages, meta = _pages_from_text_file(content)

        if len(pages) > config.MAX_PAGE_COUNT:
            raise ValidationError(f"{len(pages)} pages exceeds the {config.MAX_PAGE_COUNT}-page limit")

        with ENGINE_LOCK:
            engine = get_engine()
            before = len(engine.chunks)
            engine.add_document(doc.id, pages, page_meta=meta, embed=True)
            chunk_count = len(engine.chunks) - before

        doc.page_count = len(pages)
        doc.chunk_count = chunk_count
        doc.ocr_pages = sum(1 for m in meta if m.get("source") == "ocr")
        doc.status = "ready"
        doc.error_message = "; ".join(notes) if notes else None
        db.add(AuditRecord(
            workspace_id=doc.workspace_id, event_type="document.ingested", document_id=doc.id,
            detail=f"pages={len(pages)} chunks={chunk_count} ocr_pages={doc.ocr_pages} "
                   f"elapsed_s={time.perf_counter()-t0:.2f}",
        ))
        db.commit()
        logger.info("Ingested document %s (%s): %d pages, %d chunks in %.2fs",
                     doc.id, doc.filename, len(pages), chunk_count, time.perf_counter() - t0)
    except Exception as ex:  # noqa: BLE001 -- must not crash the background task silently
        doc.status = "failed"
        doc.error_message = str(ex)[:2000]
        db.add(AuditRecord(
            workspace_id=doc.workspace_id, event_type="document.ingest_failed", document_id=doc.id, detail=str(ex)[:2000],
        ))
        db.commit()
        logger.exception("Ingestion failed for document %s (%s)", document_id, doc.filename)


def delete_document(doc: Document, db: Session) -> int:
    """Removes the document from the in-process engine (chunks + reindexed
    vectors/BM25), deletes its stored file, marks the DB row deleted, and
    writes an audit record -- the full chain Phase 4 requires ('deleting a
    document must remove or invalidate all corresponding derived content').
    Returns the number of chunks removed, which the caller uses to verify
    deletion actually happened rather than assuming it did."""
    with ENGINE_LOCK:
        engine = get_engine()
        removed = engine.remove_document(doc.id, embed=True)
    try:
        if os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
    except OSError:
        logger.warning("Could not remove stored file for document %s at %s", doc.id, doc.storage_path)
    doc.status = "deleted"
    import datetime
    doc.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    db.add(AuditRecord(
        workspace_id=doc.workspace_id, event_type="document.deleted", document_id=doc.id,
        detail=f"chunks_removed={removed}",
    ))
    db.commit()
    return removed
