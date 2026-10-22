"""Pydantic request/response schemas for the FastAPI backend."""
import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    content_hash: str
    file_size_bytes: int
    page_count: int | None
    chunk_count: int | None
    ocr_pages: int | None
    error_message: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
    total: int


class DeleteResult(BaseModel):
    document_id: str
    chunks_removed: int
    verified_not_retrievable: bool


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int | None = None
    mode: str = Field(default="Hybrid", pattern="^(Dense only|Lexical only|Hybrid)$")
    generation_provider: str | None = None  # overrides config.GENERATION_PROVIDER for this call


class EvidenceOut(BaseModel):
    chunk_id: str
    document: str
    page: int
    text: str
    source: str
    ocr_confidence: float | None
    score: float


class EARSignals(BaseModel):
    agreement: float
    ocr_confidence: float
    contradiction: float
    complexity: float


class AskResponse(BaseModel):
    query: str
    decision: str  # answer | expand_retrieval | inspect_structure | abstain
    probability: float
    reason: str
    signals: EARSignals
    answer: str | None
    generation_provider: str | None
    evidence: list[EvidenceOut]
    citations_verified: bool
    latency_ms: float


class HealthOut(BaseModel):
    status: str
    device: str
    embedding_backend: str
    reranker_loaded: bool
    documents_indexed: int
    chunks_indexed: int
    ollama_available: bool
    ear_calibration_loaded: bool
    auth_enabled: bool
    database_url_scheme: str
