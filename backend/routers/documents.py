"""Document Library / Processing Studio endpoints: upload, list, status,
delete-with-verification. Backed by ingestion.py for the actual pipeline."""
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..ingestion import ValidationError, content_hash, delete_document, process_document, validate_upload
from ..models import AuditRecord, Document
from ..schemas import DeleteResult, DocumentListOut, DocumentOut
from ..security import require_api_key

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    content = await file.read()
    try:
        validate_upload(file.filename, content)
    except ValidationError as ex:
        raise HTTPException(422, str(ex))

    h = content_hash(content)
    existing = db.execute(
        select(Document).where(
            Document.content_hash == h,
            Document.workspace_id == config.DEFAULT_WORKSPACE_ID,
            Document.status != "deleted",
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Duplicate detection (Phase 4): return the existing record rather
        # than re-ingesting identical bytes a second time.
        return existing

    doc_id = str(uuid.uuid4())
    storage_path = os.path.join(config.UPLOAD_DIR, f"{doc_id}{os.path.splitext(file.filename)[1].lower()}")
    with open(storage_path, "wb") as f:
        f.write(content)

    doc = Document(
        id=doc_id,
        workspace_id=config.DEFAULT_WORKSPACE_ID,
        owner_id=config.DEFAULT_OWNER_ID,
        filename=file.filename,
        content_hash=h,
        file_size_bytes=len(content),
        storage_path=storage_path,
        status="processing",
    )
    db.add(doc)
    db.add(AuditRecord(workspace_id=doc.workspace_id, event_type="document.uploaded", document_id=doc.id,
                        detail=f"filename={file.filename} size={len(content)}"))
    db.commit()
    db.refresh(doc)

    # Background processing (Phase 4) -- the request returns immediately
    # with status="processing"; poll GET /documents/{id} for completion.
    background_tasks.add_task(_process_in_background, doc.id)
    return doc


def _process_in_background(document_id: str):
    from ..db import SessionLocal
    db = SessionLocal()
    try:
        process_document(document_id, db)
    finally:
        db.close()


@router.get("", response_model=DocumentListOut)
def list_documents(db: Session = Depends(get_db), include_deleted: bool = False):
    q = select(Document).where(Document.workspace_id == config.DEFAULT_WORKSPACE_ID)
    if not include_deleted:
        q = q.where(Document.status != "deleted")
    q = q.order_by(Document.created_at.desc())
    docs = list(db.execute(q).scalars())
    return DocumentListOut(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.delete("/{document_id}", response_model=DeleteResult)
def delete_document_endpoint(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    if doc.status == "deleted":
        raise HTTPException(409, "Document already deleted")

    removed = delete_document(doc, db)

    # Deletion verification (Phase 4: "implement deletion verification"):
    # actually query the live engine's chunk list, not just trust the count.
    from ..engine_singleton import get_engine
    engine = get_engine()
    still_present = any(c["document"] == doc.id for c in engine.chunks)

    return DeleteResult(document_id=doc.id, chunks_removed=removed, verified_not_retrievable=not still_present)
