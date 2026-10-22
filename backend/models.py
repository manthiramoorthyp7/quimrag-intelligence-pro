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
    ('routing audit records'), plus the raw signal values for later analysis.
    answer_text/evidence_json/generation_provider are stored so a later,
    on-demand POST /verify/{query_record_id} call (backend/claim_verification.py)
    can run claim-level verification against the EXACT evidence the answer
    was actually generated from, without needing to re-retrieve (which could
    return different results if the index changed since)."""
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
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class ClaimVerificationRecord(Base):
    """One row per POST /verify call -- persists the full claim-level
    verification + evidence-lineage + counterfactual-test result so it can
    be retrieved again without re-running (expensive, multi-LLM-call) work,
    and so the UI's verification history is real stored data, not recomputed
    on every page view."""
    __tablename__ = "claim_verification_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_record_id: Mapped[int] = mapped_column(Integer, ForeignKey("query_records.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    judge_model: Mapped[str] = mapped_column(String(128))
    n_claims: Mapped[int] = mapped_column(Integer)
    n_supported: Mapped[int] = mapped_column(Integer)
    n_contradicted: Mapped[int] = mapped_column(Integer)
    n_unsupported: Mapped[int] = mapped_column(Integer)
    n_counterfactual_tested: Mapped[int] = mapped_column(Integer)
    n_counterfactual_sensitive: Mapped[int] = mapped_column(Integer)
    result_json: Mapped[str] = mapped_column(Text)  # full claim_verification.verify_answer() output
    latency_ms: Mapped[float] = mapped_column()
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
