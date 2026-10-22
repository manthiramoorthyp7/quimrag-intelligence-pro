"""Claim-level Evidence Verification with Evidence Lineage and a Counterfactual
Evidence-Deletion Test (EICV-RAG, scoped implementation).

This is the research layer requested in the EICV-RAG prompt, implemented as
the specific, defensible slice of it that is actually buildable on this
project's existing infrastructure in one pass, rather than the full 18-part
system (evidence graph DB, 7 counterfactual test types, adaptive budget
policy, 13-baseline benchmark). What is NOT built here is listed explicitly
in docs/production/EICV_RAG.md, not silently omitted.

Design, reusing proven infrastructure rather than inventing a new pattern:
- Claim extraction reuses quimrag.ragas_eval._extract_claims's two-step
  design (extract claims from the answer with NO context shown first) --
  found during this project's earlier RAGAS work to avoid a real bug where
  small local judge models list context sentences as if they were claims
  when context and answer are shown together in one call.
- Evidence attribution: a second judge call, now WITH all retrieved evidence
  shown (each chunk prefixed by its real chunk_id), asks which chunk_id(s)
  actually support each claim and whether support is SUPPORTED, CONTRADICTED,
  or UNSUPPORTED -- this is the claim-to-evidence attribution step, distinct
  from (and a strict superset of) citation-marker validation
  (backend/citations.py), which only checks a citation POINTS to a real
  chunk, not that the chunk actually SUPPORTS the claim.
- Evidence lineage: for each claim, the full document -> page -> chunk ->
  retrieval-rank -> source/OCR-confidence chain for every chunk the judge
  identified as supporting it, assembled from data already computed by
  retrieval (no fabricated bounding boxes, no invented OCR confidence --
  only fields quimrag.core actually populates are included, and an absent
  field is reported as null, not guessed).
- Counterfactual Test 1 (evidence deletion, EICV-RAG Part B TEST 1): for each
  SUPPORTED claim, remove its identified supporting chunk(s) from the
  evidence set and re-run the SAME attribution judge call against the
  reduced set. If the claim is now UNSUPPORTED, that claim's support is
  genuinely dependent on the removed evidence (high confidence); if it
  remains SUPPORTED, the claim is either backed by redundant evidence still
  present or the judge/model has independent (parametric or duplicated)
  support for it -- reported as a diagnostic finding, explicitly NOT treated
  as proof of hallucination or of correctness either way, per the EICV-RAG
  prompt's own stated caveat.

This module makes LLM calls and is therefore slow (several seconds per
claim) -- it is deliberately NOT run on every /ask call. It is exposed as a
separate, on-demand endpoint (POST /verify) so verification cost is spent
only when requested, consistent with the "adaptive verification budget"
framing: cheap signals (EAR) gate every query; this expensive, deeper check
runs only when asked for.
"""
import re

from quimrag.local_llm import generate

JUDGE_MODEL_DEFAULT = "llama3.2:latest"
_VERDICT_RE = re.compile(r"^(\d+)[.)]\s*(SUPPORTED|CONTRADICTED|UNSUPPORTED)\b.*?(?:\[([^\]]*)\])?\s*$")


def extract_claims(answer_text: str, judge_model: str = JUDGE_MODEL_DEFAULT, timeout: int = 60) -> list[str]:
    """Same two-step-safe extraction as quimrag.ragas_eval._extract_claims:
    NO evidence context is shown in this call, only the answer text, which
    is what prevents the judge from listing context sentences as claims."""
    if not answer_text or not answer_text.strip():
        return []
    # Strip [C12]-style citation markers before extraction -- found during
    # this module's own development that a small local judge otherwise
    # treats a literal "[C1]" marker as part of the claim's text (e.g.
    # "[C1] discusses product line." as a standalone "claim"), which is a
    # citation-rendering artifact, not a fact the answer asserts.
    clean_text = re.sub(r"\[C\d+(?:,\s*C\d+)*\]", "", answer_text).strip()
    clean_text = re.sub(r"\s{2,}", " ", clean_text)
    prompt = (
        f"ANSWER:\n{clean_text}\n\n"
        "List each distinct factual claim made in the ANSWER above, one per numbered line. "
        "No other text, no commentary."
    )
    resp = generate(prompt, model=judge_model, timeout=timeout, temperature=0)
    claims = []
    for line in resp.splitlines():
        line = line.strip()
        m = re.match(r"^\d+[.)]\s*(.+)$", line)
        if m:
            claims.append(m.group(1).strip())
    return claims


def _attribute_claims(claims: list[str], evidence: list[dict], judge_model: str, timeout: int = 90) -> dict[int, dict]:
    """One batched judge call: for each claim, returns {status, chunk_ids}.
    Evidence shown WITH real chunk_ids so the judge can name which chunk(s)
    actually support a claim, not just whether "the context" in general does."""
    if not claims or not evidence:
        return {}
    context_text = "\n".join(f"[{e['chunk_id']}] ({e['document']}, page {e['page']}): {e['text'][:400]}" for e in evidence)
    numbered_claims = "\n".join(f"{i+1}. {c}" for i, c in enumerate(claims))
    prompt = (
        f"EVIDENCE PASSAGES:\n{context_text}\n\nCLAIMS:\n{numbered_claims}\n\n"
        "For each numbered claim, decide: does any evidence passage SUPPORT it, does any evidence passage "
        "CONTRADICT it, or is it UNSUPPORTED by all passages shown? "
        "If SUPPORTED or CONTRADICTED, name the exact chunk id(s) responsible in brackets. "
        "Format each line EXACTLY as one of:\n"
        "1. SUPPORTED [C12]\n1. SUPPORTED [C3,C7]\n1. CONTRADICTED [C5]\n1. UNSUPPORTED\n"
        "One line per claim, no other text."
    )
    resp = generate(prompt, model=judge_model, timeout=timeout, temperature=0)
    out = {}
    for line in resp.splitlines():
        line = line.strip()
        m = _VERDICT_RE.match(line)
        if m:
            idx = int(m.group(1))
            status = m.group(2)
            chunk_ids = [c.strip() for c in (m.group(3) or "").split(",") if c.strip()]
            out[idx] = {"status": status, "chunk_ids": chunk_ids}
    return out


def _lineage_for_chunks(chunk_ids: list[str], evidence: list[dict]) -> list[dict]:
    """Assembles the document -> page -> chunk -> retrieval provenance chain
    for the given chunk ids, using only fields quimrag.core actually
    populates (no fabricated bounding boxes or OCR confidence)."""
    by_id = {e["chunk_id"]: e for e in evidence}
    lineage = []
    for i, e in enumerate(evidence):
        if e["chunk_id"] not in chunk_ids:
            continue
        lineage.append({
            "chunk_id": e["chunk_id"],
            "document_id": e["document"],
            "page": e["page"],
            "source": e.get("source"),
            "ocr_confidence": e.get("ocr_confidence"),
            "retrieval_rank": i + 1,
            "retrieval_score": e.get("score"),
            "text_excerpt": e["text"][:300],
        })
    return lineage


def verify_answer(
    answer_text: str,
    evidence: list[dict],
    judge_model: str = JUDGE_MODEL_DEFAULT,
    run_counterfactual: bool = True,
) -> dict:
    """Full claim-level verification pipeline: extract -> attribute -> build
    lineage -> (optionally) counterfactual-test each supported claim.
    Returns a JSON-serializable dict; never raises on a judge-parsing
    failure -- a claim whose verdict could not be parsed is marked
    status="UNPARSEABLE" rather than silently dropped or guessed."""
    claims = extract_claims(answer_text, judge_model)
    if not claims:
        return {"claims": [], "overall": {"n_claims": 0, "n_supported": 0, "n_contradicted": 0,
                                           "n_unsupported": 0, "claim_support_rate": None,
                                           "n_counterfactual_sensitive": 0, "n_counterfactual_tested": 0}}

    attributions = _attribute_claims(claims, evidence, judge_model)

    claim_results = []
    n_supported = n_contradicted = n_unsupported = n_cf_sensitive = n_cf_tested = 0
    for i, claim_text in enumerate(claims, start=1):
        attr = attributions.get(i)
        if attr is None:
            claim_results.append({
                "claim_id": f"claim_{i}", "text": claim_text, "support_status": "UNPARSEABLE",
                "supporting_chunk_ids": [], "evidence_lineage": [], "counterfactual": None,
            })
            continue
        status = attr["status"]
        chunk_ids = [c for c in attr["chunk_ids"] if c in {e["chunk_id"] for e in evidence}]
        lineage = _lineage_for_chunks(chunk_ids, evidence)
        if status == "SUPPORTED":
            n_supported += 1
        elif status == "CONTRADICTED":
            n_contradicted += 1
        else:
            n_unsupported += 1

        counterfactual = None
        if run_counterfactual and status == "SUPPORTED" and chunk_ids:
            reduced_evidence = [e for e in evidence if e["chunk_id"] not in chunk_ids]
            n_cf_tested += 1
            if reduced_evidence:
                re_attr = _attribute_claims([claim_text], reduced_evidence, judge_model)
                new_status = re_attr.get(1, {}).get("status", "UNPARSEABLE")
            else:
                new_status = "UNSUPPORTED"  # no evidence left at all -- trivially unsupported
            changed = new_status != "SUPPORTED"
            if changed:
                n_cf_sensitive += 1
            counterfactual = {
                "test": "evidence_deletion", "removed_chunk_ids": chunk_ids,
                "support_after_removal": new_status, "support_changed": changed,
            }

        claim_results.append({
            "claim_id": f"claim_{i}", "text": claim_text, "support_status": status,
            "supporting_chunk_ids": chunk_ids, "evidence_lineage": lineage,
            "counterfactual": counterfactual,
        })

    n_total = len(claims)
    return {
        "claims": claim_results,
        "overall": {
            "n_claims": n_total, "n_supported": n_supported, "n_contradicted": n_contradicted,
            "n_unsupported": n_unsupported, "claim_support_rate": n_supported / n_total if n_total else None,
            "n_counterfactual_tested": n_cf_tested, "n_counterfactual_sensitive": n_cf_sensitive,
        },
    }
