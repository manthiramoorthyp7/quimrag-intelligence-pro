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
    query_record_id: int
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


class VerifyRequest(BaseModel):
    judge_model: str | None = None  # defaults to claim_verification.JUDGE_MODEL_DEFAULT
    run_counterfactual: bool = True


class EvidenceLineageOut(BaseModel):
    chunk_id: str
    document_id: str
    page: int
    source: str | None
    ocr_confidence: float | None
    retrieval_rank: int
    retrieval_score: float | None
    text_excerpt: str


class CounterfactualOut(BaseModel):
    test: str
    removed_chunk_ids: list[str]
    support_after_removal: str
    support_changed: bool


class ClaimOut(BaseModel):
    claim_id: str
    text: str
    support_status: str  # SUPPORTED | CONTRADICTED | UNSUPPORTED | UNPARSEABLE
    supporting_chunk_ids: list[str]
    evidence_lineage: list[EvidenceLineageOut]
    counterfactual: CounterfactualOut | None


class VerifyOverview(BaseModel):
    n_claims: int
    n_supported: int
    n_contradicted: int
    n_unsupported: int
    claim_support_rate: float | None
    n_counterfactual_tested: int
    n_counterfactual_sensitive: int


class VerifyResponse(BaseModel):
    query_record_id: int
    judge_model: str
    claims: list[ClaimOut]
    overall: VerifyOverview
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
