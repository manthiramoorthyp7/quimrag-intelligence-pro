"""Claim-level verification endpoint (EICV-RAG layer): on-demand, deeper
check of a previously-generated answer -- claim extraction, per-claim
evidence attribution with document/page/chunk lineage, and a counterfactual
evidence-deletion test. Separate from /ask by design (adaptive verification
budget: cheap EAR routing runs on every query; this expensive, multi-LLM-
call check runs only when explicitly requested)."""
import json
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import config
from ..claim_verification import JUDGE_MODEL_DEFAULT, verify_answer
from ..db import get_db
from ..models import ClaimVerificationRecord, QueryRecord
from ..schemas import VerifyRequest, VerifyResponse
from ..security import require_api_key

router = APIRouter(prefix="/verify", tags=["verify"], dependencies=[Depends(require_api_key)])


@router.post("/{query_record_id}", response_model=VerifyResponse)
def verify(query_record_id: int, req: VerifyRequest, db: Session = Depends(get_db)):
    record = db.get(QueryRecord, query_record_id)
    if record is None:
        raise HTTPException(404, "query_record_id not found")
    if not record.answer_text:
        raise HTTPException(409, "This query has no generated answer to verify (decision was "
                                  f"'{record.decision}', which produces no answer text by design)")
    if not record.evidence_json:
        raise HTTPException(409, "No stored evidence for this query record -- cannot verify")

    evidence = json.loads(record.evidence_json)
    judge_model = req.judge_model or JUDGE_MODEL_DEFAULT

    t0 = time.perf_counter()
    result = verify_answer(record.answer_text, evidence, judge_model=judge_model,
                            run_counterfactual=req.run_counterfactual)
    latency_ms = (time.perf_counter() - t0) * 1000

    overall = result["overall"]
    db.add(ClaimVerificationRecord(
        query_record_id=query_record_id, workspace_id=config.DEFAULT_WORKSPACE_ID, judge_model=judge_model,
        n_claims=overall["n_claims"], n_supported=overall["n_supported"],
        n_contradicted=overall["n_contradicted"], n_unsupported=overall["n_unsupported"],
        n_counterfactual_tested=overall["n_counterfactual_tested"],
        n_counterfactual_sensitive=overall["n_counterfactual_sensitive"],
        result_json=json.dumps(result), latency_ms=latency_ms,
    ))
    db.commit()

    return VerifyResponse(query_record_id=query_record_id, judge_model=judge_model,
                           claims=result["claims"], overall=overall, latency_ms=latency_ms)


@router.get("/{query_record_id}/history")
def verify_history(query_record_id: int, db: Session = Depends(get_db)):
    """Previously-computed verification results for this query, newest
    first -- real stored history, not recomputed on page load."""
    rows = (
        db.query(ClaimVerificationRecord)
        .filter(ClaimVerificationRecord.query_record_id == query_record_id)
        .order_by(ClaimVerificationRecord.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id, "judge_model": r.judge_model, "n_claims": r.n_claims, "n_supported": r.n_supported,
            "n_contradicted": r.n_contradicted, "n_unsupported": r.n_unsupported,
            "n_counterfactual_tested": r.n_counterfactual_tested,
            "n_counterfactual_sensitive": r.n_counterfactual_sensitive,
            "latency_ms": r.latency_ms, "created_at": r.created_at.isoformat(),
            "result": json.loads(r.result_json),
        }
        for r in rows
    ]
