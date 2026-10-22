# EICV-RAG: Evidence Integrity & Counterfactual Verification — Scoped Implementation

The EICV-RAG prompt that motivated this work specifies an 18-part research-and-engineering program: an evidence lineage graph database, 7 distinct counterfactual test types, a learned claim-integrity score with 5 compared model variants, an adaptive verification-budget policy, a full literature review, OHR-Bench re-acquisition with document-disjoint splits, 14 baseline/ablation configurations, 30 robustness/adversarial scenarios, Playwright browser automation, and a new research paper — genuinely multi-week, multi-person scope.

This document states plainly what was actually built in this pass, what was deliberately left out and why, and what the real, verified evidence for each built piece is — consistent with this project's standing rule throughout this session: evidence first, claims second.

## What was built and verified this pass

### 1. Claim-level evidence verification (`backend/claim_verification.py`)

For a previously-generated answer: extracts atomic claims (reusing the proven two-step, no-context-shown-first pattern from `quimrag/ragas_eval.py`, which avoids a documented bug where small local judges list context sentences as claims when context and answer are shown together), then attributes each claim to the specific evidence chunk_id(s) that support it via a second judge call that sees the real chunk ids.

**This is a strict superset of citation-marker validation** (`backend/citations.py`, which only checks a `[C12]` marker points to a real chunk, not that the chunk supports the claim) — EICV's attribution step independently re-derives support, so it also catches a citation that resolves to a real chunk but doesn't actually support the claim it's attached to.

**Verified:** real end-to-end runs via `curl` and a live browser session (not mocked) against a real local document and a real Ollama judge (`llama3.2:latest`). Observed outputs include correctly SUPPORTED claims with correct chunk attribution, and — honestly, not hidden — at least one false-negative UNSUPPORTED verdict on a claim that was in fact stated verbatim in the evidence, and inconsistent bracket-citation compliance in the judge's output format. This is consistent with this project's own prior documented finding (`quimrag/ragas_eval.py`'s module docstring) that small local judge models have real reliability limits, not a new, hidden problem.

### 2. Evidence lineage

For each claim, the document → page → chunk → retrieval-rank → source/OCR-confidence chain is assembled from fields `quimrag/core.py` actually populates. **No bounding boxes, no fabricated OCR confidence** — the full relational-graph schema the original prompt describes (tables, cell-level provenance, transformation history) was not built; this is the lighter-weight, explicitly-permitted alternative ("Start with a lightweight relational schema... Do not introduce an unnecessarily complex graph database").

### 3. One counterfactual test: evidence deletion (TEST 1 of the prompt's 7)

For each SUPPORTED claim, its supporting chunk(s) are removed from the evidence set and the attribution judge is re-run on the reduced set. **Verified, real, repeatable finding**: in manual testing, a claim's support genuinely flipped from SUPPORTED to UNSUPPORTED when its sole supporting chunk was removed — a clean, real demonstration of the mechanism, not a synthetic example. Per the prompt's own explicit caveat, this is reported as a diagnostic signal of evidence dependence, **not proof of correctness or hallucination**, and the UI states this distinction (`support unchanged` is captioned as "possibly redundant evidence or model's own knowledge," not as a pass/fail verdict).

### 4. A real, independently-storable audit trail

`QueryRecord` now persists `answer_text`/`evidence_json` so verification can be re-run or re-inspected without re-retrieving (which could silently change if the index changed). `ClaimVerificationRecord` persists every verification run with its full result, queryable via `GET /verify/{id}/history` — real stored history, not recomputed on every view.

### 5. A real correctness bug found and fixed: restart recovery

Found during this pass's own manual verification (not assumed, not hypothetical): after a process restart, `Document` rows persisted in SQLite still showed `status="ready"`, but the actual retrieval index lived only in the in-process engine and was empty — a document could look retrievable while genuinely not being so. Fixed with `rebuild_index_from_storage()`, called at backend startup, which re-ingests every "ready" document's stored file back into the engine. **Verified**: killed and restarted the server, confirmed `chunks_indexed` went from 1→0→1 across the restart, confirmed `/ask` worked immediately post-restart with no manual re-upload. Covered by a new regression test (`tests/test_backend_api.py::test_restart_recovery_rebuilds_index_from_storage`).

### 6. A completely rebuilt frontend (`frontend/index.html`)

A ChatGPT-style interface (not a copy of OpenAI's branding — layout pattern only): collapsible sidebar with new-chat/search/conversation history (persisted to `localStorage`, genuinely per-browser, not fake data) and a Document Library entry point; a main chat column with citation-linked answers, an EAR decision badge, expandable Sources and Claim-level Verification panels (the latter calling `/verify` on demand — the "adaptive verification budget" principle: cheap EAR routing runs on every query, expensive multi-LLM-call verification only runs when asked for), and an optional Debug panel showing the real EAR signal values, probability, and latency for every answer. A Document Library modal handles upload/status/delete.

**Verified by actually driving it**, not just writing it: a file was injected via `DataTransfer` (the Browser pane has no native file picker), the Upload/Ask/Verify/Delete buttons were clicked, and each resulting state change was confirmed via `get_page_text`/DOM inspection and screenshots. **Two real bugs were found and fixed during this verification, not before it**: (a) on a narrow viewport, the overlay sidebar covered its own toggle button, making it permanently unreachable — fixed by raising the toggle's z-index and defaulting the sidebar closed on narrow screens; (b) after running claim verification, the results panel silently re-collapsed on the next re-render because `<details open>` state wasn't persisted on the message object — fixed by tracking `sourcesOpen`/`verifyOpen` flags per message and both the native `toggle` event and the action-button click path.

### 7. Tests

9 new unit tests (`tests/test_claim_verification.py`, judge mocked — deterministic, no Ollama required) covering claim extraction's citation-stripping, attribution parsing (including multi-chunk-id parsing and malformed-line tolerance), lineage assembly, and the full pipeline's counterfactual-sensitivity detection. 5 new integration tests in `tests/test_backend_api.py` (the `/verify` end-to-end loop against a real backend, the 404/409 error paths, and the restart-recovery regression test). **Full suite: 91 passed, 1 skipped** (up from 78 before this pass).

## What was explicitly NOT built this pass, and why

| Prompt requirement | Status | Why |
|---|---|---|
| Full evidence-lineage graph DB (tables, cell-level provenance, bounding boxes, transformation history) | Not built | Explicitly permitted to use a lighter-weight design instead; no genuine bounding-box or cell-level data is available from the current extraction pipeline to populate it honestly |
| Counterfactual TEST 2-7 (masking, replacement, distractor injection, OCR perturbation, citation substitution, redundant-evidence controls) | Not built | TEST 1 alone already required 3 new LLM-call types; the remaining 6 are each a comparable scope of work, deferred as named follow-ups, not silently dropped |
| Claim-Level Evidence Integrity Score (a single learned/calibrated score combining 10 signals, compared across 5 model variants) | Not built | Would require the labeled dataset and document-disjoint calibration/evaluation infrastructure this project's `research/FINAL_VALIDATION/` work already built for EAR — reusing it properly for a second, different scoring target is real follow-up work, not reused here |
| Adaptive Verification Budget (token/latency/cost-aware routing policy) | Partially present only as a design principle (verification is opt-in per-query via the UI, not run automatically) — no formal budget optimizer | A real budget policy needs the usage data (verification call frequency, cost) this pass does not yet collect |
| Literature review (`docs/RELATED_WORK_AND_NOVELTY.md`) | Not written | Requires actual web-search-verified citations; not attempted this pass rather than inventing or guessing sources |
| OHR-Bench re-acquisition, document-disjoint train/calibration/eval splits for EICV specifically | Not done | The EAR document-disjoint-split infrastructure exists (`research/FINAL_VALIDATION/`) but was not re-run for a claim-verification-specific evaluation this pass |
| 14 baselines/ablations (B0-B13) | Not run | No comparative benchmark was executed for the claim-verification layer; only the mechanism's correctness was manually and automatically verified, not its comparative accuracy against alternatives |
| 30-scenario robustness/adversarial suite | Not run | Out of scope for this pass; the existing security validation (MIME-spoofing, extension allowlisting — `docs/production/INITIAL_AUDIT.md`) is unchanged and unexpanded |
| Playwright browser E2E suite | Not built | Manual verification via the Claude Browser pane tooling was used instead, confirmed working but not automated into a repeatable CI-runnable suite |
| Full research paper covering EICV-RAG | Not written | The existing `research/PUBLICATION_PACKAGE/QuIM_EAR_Revalidation_Paper.docx` covers EAR, RVQ, and the production backend; a further revision folding in EICV-RAG would need the evaluation data this pass did not generate |

## Bottom line

What exists now is a genuinely working, correctly-attributed, counterfactually-testable claim verification layer with real evidence lineage, wired into a real UI and verified by actually running it — not the full EICV-RAG research program. The single most valuable immediate next step, if this continues, is Counterfactual TEST 4 (distractor injection) or TEST 6 (citation substitution), since both reuse the exact `_attribute_claims` machinery already built and tested here, unlike the other remaining tests which need new infrastructure (OCR perturbation needs the degradation pipeline already in `research/data/ocr_degradation.py`; masking needs span-level text editing not yet implemented).
