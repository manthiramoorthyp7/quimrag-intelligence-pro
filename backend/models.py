"""Document/job/audit metadata models. The engine's actual chunk/vector state
lives in the in-process QuIMRAG instance (engine_singleton.py) -- this table
is the durable record of WHAT was uploaded and its processing status, which
is what was previously entirely missing (see docs/production/INITIAL_AUDIT.md
#2, #8). `workspace_id`/`owner_id` exist from day one so a future multi-user
mode does not require a schema migration (ARCHITECTURE_DECISIONS.md #1)."""
import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    owner_id: Mapped[str] = mapped_column(String(64), default="local-user")
    filename: Mapped[str] = mapped_column(String(512))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(32), default="processing", index=True)
    # processing | ready | failed | deleted
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    document_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("documents.id"), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class QueryRecord(Base):
    """One row per /ask call -- the EAR routing audit trail Phase 5 requires
    ('routing audit records'), plus the raw signal values for later analysis."""
    __tablename__ = "query_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    query: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    probability: Mapped[float] = mapped_column()
    signal_agreement: Mapped[float] = mapped_column()
    signal_ocr_confidence: Mapped[float] = mapped_column()
    signal_contradiction: Mapped[float] = mapped_column()
    signal_complexity: Mapped[float] = mapped_column()
    reason: Mapped[str] = mapped_column(Text)
    n_evidence: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
