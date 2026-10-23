"""Ask QuIM endpoint: Hybrid retrieval -> EAR decision -> (if answering)
generation -> citation verification -> routing audit record. This is the
real, end-to-end implementation of Phase 5's "reliable routing" + Phase 8's
"citation validation against actual retrieved evidence". The returned
query_record_id lets the frontend trigger deeper, slower claim-level
verification (POST /verify/{id}, backend/claim_verification.py) on demand
rather than paying that cost on every query."""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from quimrag import adaptive as EAR

from .. import config
from ..citations import verify_citations
from ..db import get_db
from ..engine_singleton import ENGINE_LOCK, get_ear_model, get_engine
from ..generation import GenerationError, generate
from ..models import QueryRecord
from ..schemas import AskRequest, AskResponse, EARSignals, EvidenceOut
from ..security import require_api_key

router = APIRouter(prefix="/ask", tags=["ask"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db)):
    t0 = time.perf_counter()
    k = req.k or config.RETRIEVAL_K

    with ENGINE_LOCK:
        engine = get_engine()
        if not engine.chunks:
            raise HTTPException(409, "No documents are indexed yet -- upload and wait for ingestion to finish first")

        if req.mode == "Hybrid":
            # EAR's signals (esp. "agreement") need both the BM25 and dense
            # rankings, so adaptive routing only applies in Hybrid mode.
            ear_model = get_ear_model()
            evidence, sig, decision, probability, reason = EAR.retrieve_adaptive(engine, req.query, ear_model, k=k)
            ear_applied = True
        else:
            # Dense only / Lexical only: EAR is bypassed by request -- there is
            # no "agreement between two rankings" to compute with only one
            # ranking, so we don't fabricate a routing decision. Signals are
            # still computed (cheap, already-retrieved evidence, no extra model
            # calls) purely for display; the decision is always "answer" if
            # retrieval found anything, "abstain" if it found nothing.
            evidence = engine.retrieve(req.query, k, req.mode)
            sig = EAR.compute_signals(engine, req.query, evidence, k) if evidence else \
                {"agreement": 0.0, "ocr_confidence": 0.0, "contradiction": 0.0, "complexity": 0.0}
            decision = "answer" if evidence else "abstain"
            probability = 1.0 if evidence else 0.0
            reason = f"EAR routing bypassed -- mode={req.mode} requested explicitly"
            ear_applied = False

    answer_text = None
    provider_used = None
    citations_ok = True

    if decision in ("answer", "expand_retrieval") and evidence:
        provider = req.generation_provider or config.GENERATION_PROVIDER
        try:
            answer_text, provider_used = generate(req.query, evidence, provider, model=req.model)
            citations_ok = verify_citations(answer_text, evidence)
        except GenerationError as ex:
            raise HTTPException(502, str(ex))
    elif decision == "inspect_structure":
        answer_text = None  # evidence is surfaced for human review, no generated claim (Phase 5: don't guess)
    # decision == "abstain": answer_text stays None, by design

    latency_ms = (time.perf_counter() - t0) * 1000

    record = QueryRecord(
        workspace_id=config.DEFAULT_WORKSPACE_ID, query=req.query, decision=decision, probability=probability,
        signal_agreement=sig["agreement"], signal_ocr_confidence=sig["ocr_confidence"],
        signal_contradiction=sig["contradiction"], signal_complexity=sig["complexity"],
        reason=reason, n_evidence=len(evidence), latency_ms=latency_ms,
        answer_text=answer_text, generation_provider=provider_used,
        evidence_json=json.dumps(evidence) if evidence else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return AskResponse(
        query_record_id=record.id,
        query=req.query,
        mode_used=req.mode,
        ear_applied=ear_applied,
        decision=decision,
        probability=probability,
        reason=reason,
        signals=EARSignals(**sig),
        answer=answer_text,
        generation_provider=provider_used,
        evidence=[EvidenceOut.model_validate(e) for e in evidence],
        citations_verified=citations_ok,
        latency_ms=latency_ms,
    )
